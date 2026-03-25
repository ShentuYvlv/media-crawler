#!/usr/bin/env python3
"""
小黑盒社区帖子爬虫
用法:
    python topic_feeds_crawler.py --topic-id 416158 --limit 100
    python topic_feeds_crawler.py -t 416158 -s hot -l 50 -o output_name
    python topic_feeds_crawler.py -t 416158 -l 50 --comment-limit 30
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zipfile
from datetime import datetime
from html import unescape
from pathlib import Path
from xml.sax.saxutils import escape

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from xhh_client import XhhClient

# 默认配置
DEFAULT_LIMIT = 100
DEFAULT_PAGE_SIZE = 30
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "output"

# Excel 表头 (与原API格式一致)
FEEDS_HEADERS = [
    "平台",
    "网站链接",
    "发布时间",
    "数据",
    "用户昵称",
    "具体内容",
    "帖子详情",
    "评论",
    "作品类型",
    "作品标题",
    "点赞数量",
    "评论数量",
    "分享数量",
    "用户ID",
    "帖子ID",
    "标签",
    "更新时间",
    "是否视频",
]

TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str) -> str:
    """移除HTML标签"""
    cleaned = TAG_RE.sub("", unescape(text or ""))
    return " ".join(cleaned.split())


def format_timestamp(ts: int | str | None) -> str:
    """格式化时间戳"""
    if not ts:
        return ""
    try:
        dt = datetime.fromtimestamp(int(ts))
        return f"{dt.year:04d}年{dt.month:02d}月{dt.day:02d}日 {dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
    except (TypeError, ValueError, OSError):
        return ""


def join_tags(link: dict) -> str:
    """合并标签"""
    names = []
    for topic in link.get("topics", []):
        name = (topic or {}).get("name")
        if name and name not in names:
            names.append(name)
    for hashtag in link.get("hashtags", []):
        name = (hashtag or {}).get("name")
        if name and name not in names:
            names.append(name)
    return " | ".join(names)


def build_data_summary(link: dict) -> str:
    """构建数据摘要"""
    like_count = link.get("link_award_num", 0)
    comment_count = link.get("comment_num", 0)
    share_count = link.get("forward_num", 0)
    return f"点赞 {like_count} | 评论 {comment_count} | 分享 {share_count}"


def parse_detail_text(raw_text: str) -> str:
    """解析帖子详情的text字段（JSON格式的富文本）"""
    if not raw_text:
        return ""

    try:
        parts = json.loads(raw_text)
    except json.JSONDecodeError:
        return strip_html(raw_text)

    chunks: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("type") != "text":
            continue
        text = strip_html(part.get("text", ""))
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def count_comment_items(comment_groups: list[dict]) -> int:
    """统计评论数量"""
    total = 0
    for group in comment_groups or []:
        total += len(group.get("comment", []))
    return total


def flatten_comments(comment_groups: list[dict], max_comments: int) -> str:
    """格式化评论为字符串"""
    lines: list[str] = []
    counter = 1
    for group in comment_groups or []:
        for comment in group.get("comment", []):
            if counter > max_comments:
                return "\n".join(lines)
            user = (comment.get("user") or {}).get("username", "")
            text = strip_html(comment.get("text", ""))
            if not text:
                continue
            reply_user = (comment.get("replyuser") or {}).get("username", "")
            prefix = f"{counter}. {user}"
            if reply_user:
                prefix += f" 回复 @{reply_user}"
            lines.append(f"{prefix}: {text}")
            counter += 1
    return "\n".join(lines)


def normalize_link(link: dict) -> dict:
    """标准化帖子数据 (与原API格式一致)"""
    user = link.get("user", {})
    title = strip_html(link.get("title", ""))
    description = strip_html(link.get("description", ""))

    return {
        "平台": "小黑盒",
        "网站链接": link.get("share_url", ""),
        "发布时间": format_timestamp(link.get("create_at")),
        "数据": build_data_summary(link),
        "用户昵称": user.get("username", "") if isinstance(user, dict) else "",
        "具体内容": description,
        "帖子详情": "",  # 需要单独请求获取
        "评论": "",  # 需要单独请求获取
        "作品类型": "帖子",
        "作品标题": title,
        "点赞数量": link.get("link_award_num", 0),
        "评论数量": link.get("comment_num", 0),
        "分享数量": link.get("forward_num", 0),
        "用户ID": user.get("userid", "") if isinstance(user, dict) else str(link.get("userid", "")),
        "帖子ID": link.get("linkid", ""),
        "标签": join_tags(link),
        "更新时间": format_timestamp(link.get("modify_at")),
        "是否视频": "是" if link.get("has_video") else "否",
        # 用于获取详情的临时字段
        "_detail_link_id": link.get("linkid", ""),
        "_detail_h_src": link.get("h_src", ""),
    }


def fetch_topic_feeds(
    client: XhhClient,
    topic_id: int,
    total_limit: int = DEFAULT_LIMIT,
    sort_filter: str = "",
) -> list[dict]:
    """获取社区帖子"""
    all_links = []
    offset = 0
    page_size = DEFAULT_PAGE_SIZE
    lastval = ""

    while len(all_links) < total_limit:
        print(f"正在获取: offset={offset}, limit={page_size}, 已收集: {len(all_links)}/{total_limit}")

        try:
            response = client.topic_feeds(
                topic_id=topic_id,
                offset=offset,
                limit=page_size,
                sort_filter=sort_filter,
                lastval=lastval,
            )
        except Exception as e:
            print(f"请求失败: {e}")
            break

        result = response.get("result", {})
        if not result:
            print("响应中没有 result 字段")
            break

        links = result.get("links", [])
        if not links:
            print("没有更多帖子了")
            break

        for link in links:
            normalized = normalize_link(link)
            all_links.append(normalized)
            if len(all_links) >= total_limit:
                break

        # 更新分页参数
        offset = len(all_links)
        lastval = result.get("lastval", "")

        # 请求间隔，避免请求过快
        time.sleep(0.5)

    return all_links


class RateLimitError(Exception):
    """403限流错误"""
    pass


def enrich_row_with_detail(client: XhhClient, row: dict, comment_limit: int) -> dict:
    """获取单个帖子的详情和评论"""
    import urllib.error

    link_id = row.get("_detail_link_id")
    h_src = row.get("_detail_h_src", "")
    if not link_id:
        row["帖子详情"] = ""
        row["评论"] = ""
        return row

    try:
        detail_payload = client.link_tree(link_id=link_id, h_src=h_src, page=1, index=1, limit=20)
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise RateLimitError(f"403 Forbidden link_id={link_id}")
        print(f"  获取详情失败 link_id={link_id}: {e}")
        row["帖子详情"] = ""
        row["评论"] = ""
        return row
    except Exception as e:
        print(f"  获取详情失败 link_id={link_id}: {e}")
        row["帖子详情"] = ""
        row["评论"] = ""
        return row

    result = detail_payload.get("result", {}) if isinstance(detail_payload, dict) else {}
    link = result.get("link", {}) if isinstance(result, dict) else {}
    comments = list(result.get("comments", []) if isinstance(result, dict) else [])
    total_page = int(result.get("total_page", 1) or 1) if isinstance(result, dict) else 1

    # 获取更多评论页
    for page in range(2, total_page + 1):
        if count_comment_items(comments) >= comment_limit:
            break
        try:
            page_payload = client.link_tree(
                link_id=link_id,
                h_src=h_src,
                page=page,
                index=page,
                limit=20,
                is_first=0,
            )
        except Exception:
            break
        page_result = page_payload.get("result", {}) if isinstance(page_payload, dict) else {}
        comments.extend(page_result.get("comments", []) if isinstance(page_result, dict) else [])

    # 解析帖子详情（从text字段获取完整内容）
    row["帖子详情"] = parse_detail_text(link.get("text", "")) or row.get("具体内容", "")
    row["评论"] = flatten_comments(comments, comment_limit)

    # 更新其他字段（使用详情接口返回的更准确数据）
    if link:
        row["网站链接"] = link.get("share_url") or row.get("网站链接", "")
        row["发布时间"] = format_timestamp(link.get("create_at")) or row.get("发布时间", "")
        row["数据"] = build_data_summary(link)
        row["用户昵称"] = ((link.get("user") or {}).get("username")) or row.get("用户昵称", "")
        row["作品标题"] = strip_html(link.get("title", "")) or row.get("作品标题", "")
        row["点赞数量"] = link.get("link_award_num", row.get("点赞数量", 0))
        row["评论数量"] = link.get("comment_num", row.get("评论数量", 0))
        row["分享数量"] = link.get("forward_num", row.get("分享数量", 0))
        row["用户ID"] = (link.get("user") or {}).get("userid", row.get("用户ID", ""))
        row["帖子ID"] = link.get("linkid") or row.get("帖子ID", "")
        row["标签"] = join_tags(link)
        row["更新时间"] = format_timestamp(link.get("modify_at")) or row.get("更新时间", "")
        row["是否视频"] = "是" if link.get("has_video") else "否"

    return row


def enrich_feeds_rows(client: XhhClient, rows: list[dict], comment_limit: int) -> tuple[list[dict], bool]:
    """批量获取帖子详情和评论，遇到403时自动暂停重试

    返回: (已获取的数据列表, 是否完成全部)
    """
    enriched_rows: list[dict] = []
    total = len(rows)
    retry_count = 0  # 403重试计数器
    interrupted = False

    for index, row in enumerate(rows, start=1):
        link_id = row.get("帖子ID", "")
        while True:
            try:
                print(f"获取详情: {index}/{total} link_id={link_id}")
                enriched_rows.append(enrich_row_with_detail(client, row, comment_limit))
                retry_count = 0  # 成功后重置计数器
                break
            except RateLimitError as e:
                wait_time = retry_count + 1  # 等待 x+1 分钟
                print(f"  遇到403限流，等待 {wait_time} 分钟后重试... (retry_count={retry_count})")
                time.sleep(wait_time * 60)
                retry_count += 1
                # 继续循环重试当前帖子，直到成功
            except KeyboardInterrupt:
                print(f"\n\n用户中断! 已获取 {len(enriched_rows)}/{total} 条数据")
                interrupted = True
                break

        if interrupted:
            break

        # 请求间隔，避免请求过快
        time.sleep(0.3)

    return enriched_rows, not interrupted


def column_letter(index: int) -> str:
    """获取Excel列字母"""
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def xml_cell(cell_ref: str, value: object) -> str:
    """生成Excel单元格XML"""
    if value is None:
        return f'<c r="{cell_ref}"/>'
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'
    text = escape(str(value)).replace("\n", "&#10;")
    return f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def save_xlsx(rows: list[dict], output_path: Path) -> None:
    """保存为Excel文件"""
    all_rows = [FEEDS_HEADERS] + [[row.get(h, "") for h in FEEDS_HEADERS] for row in rows]

    widths = []
    for col_idx, header in enumerate(FEEDS_HEADERS):
        values = [header] + [row[col_idx] for row in all_rows[1:]]
        max_len = max(len(str(v)) if v is not None else 0 for v in values)
        widths.append(min(max(max_len + 2, 12), 80))

    cols_xml = "".join(
        f'<col min="{idx}" max="{idx}" width="{w}" customWidth="1"/>'
        for idx, w in enumerate(widths, start=1)
    )

    row_xml_parts = []
    for row_idx, row_values in enumerate(all_rows, start=1):
        cells_xml = "".join(
            xml_cell(f"{column_letter(col_idx)}{row_idx}", val)
            for col_idx, val in enumerate(row_values, start=1)
        )
        row_xml_parts.append(f'<row r="{row_idx}">{cells_xml}</row>')

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<cols>{cols_xml}</cols>'
        f'<sheetData>{"".join(row_xml_parts)}</sheetData>'
        '</worksheet>'
    )

    content_types_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '</Types>'
    )

    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="社区帖子" sheetId="1" r:id="rId1"/></sheets>'
        '</workbook>'
    )

    workbook_rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        '</Relationships>'
    )

    styles_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
        '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
        '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
        '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
        '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
        '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
        '</styleSheet>'
    )

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types_xml)
        archive.writestr("_rels/.rels", rels_xml)
        archive.writestr("xl/workbook.xml", workbook_xml)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels_xml)
        archive.writestr("xl/styles.xml", styles_xml)
        archive.writestr("xl/worksheets/sheet1.xml", sheet_xml)


# 默认评论数量限制
DEFAULT_COMMENT_LIMIT = 100


def main():
    parser = argparse.ArgumentParser(description="小黑盒社区帖子爬虫")
    parser.add_argument(
        "--topic-id", "-t",
        type=int,
        required=True,
        help="社区/话题ID (例如: 416158 = 情投一盒)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=DEFAULT_LIMIT,
        help=f"爬取帖子数量 (默认: {DEFAULT_LIMIT})",
    )
    parser.add_argument(
        "--comment-limit", "-c",
        type=int,
        default=DEFAULT_COMMENT_LIMIT,
        help=f"每个帖子最大评论数量 (默认: {DEFAULT_COMMENT_LIMIT}, 设为0则不获取评论和详情)",
    )
    parser.add_argument(
        "--sort", "-s",
        choices=["hot", "new"],
        default="new",
        help="排序方式: hot=热门, new=最新 (默认: new)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="",
        help="输出文件名前缀 (默认: topic_feeds_<topic_id>)",
    )
    args = parser.parse_args()

    # 排序参数
    sort_filter = "hot-rank" if args.sort == "hot" else ""
    sort_name = "热门" if args.sort == "hot" else "最新"

    # 输出文件名
    output_prefix = args.output or f"topic_feeds_{args.topic_id}"

    # 创建输出目录
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("小黑盒社区帖子爬虫")
    print("=" * 60)
    print(f"社区ID: {args.topic_id}")
    print(f"排序方式: {sort_name}")
    print(f"目标数量: {args.limit}")
    print(f"评论数量: {args.comment_limit if args.comment_limit > 0 else '不获取'}")
    print("=" * 60)

    # 创建客户端
    client = XhhClient()

    # 获取帖子列表
    links = fetch_topic_feeds(
        client=client,
        topic_id=args.topic_id,
        total_limit=args.limit,
        sort_filter=sort_filter,
    )

    if not links:
        print("未获取到任何帖子")
        return 1

    print(f"\n共获取 {len(links)} 条帖子列表")

    # 获取帖子详情和评论
    completed = True
    if args.comment_limit > 0:
        print("\n开始获取帖子详情和评论... (按Ctrl+C可中断并保存已获取数据)")
        try:
            links, completed = enrich_feeds_rows(client, links, args.comment_limit)
        except KeyboardInterrupt:
            print("\n\n用户中断!")
            completed = False

    # 保存Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = "_interrupted" if not completed else ""
    xlsx_path = DEFAULT_OUTPUT_DIR / f"{output_prefix}_{timestamp}{suffix}.xlsx"
    save_xlsx(links, xlsx_path)
    print(f"\nExcel已保存: {xlsx_path}")

    if completed:
        print("\n完成!")
    else:
        print(f"\n已保存 {len(links)} 条数据 (未完成全部)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
