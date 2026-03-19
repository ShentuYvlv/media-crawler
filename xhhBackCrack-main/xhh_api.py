#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
import zipfile
from datetime import datetime
from html import unescape
from pathlib import Path
from xml.sax.saxutils import escape

from xhh_client import XhhClient


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
ENV_PATH = BASE_DIR / ".env"
TAG_RE = re.compile(r"<[^>]+>")
DEFAULT_SEARCH_LIMIT = 10
DEFAULT_COMMENT_LIMIT = 100
SEARCH_HEADERS = [
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


def load_dotenv(env_path: Path) -> None:
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def getenv_int(name: str, default: int) -> int:
    value = os.getenv(name, "").strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def pop_int_param(params: dict[str, str], name: str, default: int) -> int:
    value = params.pop(name, "").strip()
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


def parse_params(args: list[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    index = 0

    while index < len(args):
        current = args[index]
        if current == "--query" and index + 1 < len(args):
            params["q"] = args[index + 1]
            index += 2
            continue
        if "=" in current:
            key, value = current.split("=", 1)
            params[key] = value
        index += 1

    return params


def build_output_path(route_name: str, suffix: str = ".json") -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"{route_name}_{timestamp}{suffix}"


def save_json(payload: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def column_letter(index: int) -> str:
    result = ""
    current = index
    while current > 0:
        current, remainder = divmod(current - 1, 26)
        result = chr(65 + remainder) + result
    return result


def xml_cell(cell_ref: str, value: object) -> str:
    if value is None:
        return f'<c r="{cell_ref}"/>'

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f'<c r="{cell_ref}"><v>{value}</v></c>'

    text = escape(str(value)).replace("\n", "&#10;")
    return f'<c r="{cell_ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def save_search_xlsx(rows: list[dict], output_path: Path) -> None:
    all_rows = [SEARCH_HEADERS] + [[row.get(header, "") for header in SEARCH_HEADERS] for row in rows]
    widths: list[int] = []
    for column_index, header in enumerate(SEARCH_HEADERS):
        values = [header] + [row[column_index] for row in all_rows[1:]]
        max_length = max(len(str(value)) if value is not None else 0 for value in values)
        widths.append(min(max(max_length + 2, 12), 80))

    cols_xml = "".join(
        f'<col min="{index}" max="{index}" width="{width}" customWidth="1"/>'
        for index, width in enumerate(widths, start=1)
    )

    row_xml_parts: list[str] = []
    for row_index, row_values in enumerate(all_rows, start=1):
        cells_xml = "".join(
            xml_cell(f"{column_letter(column_index)}{row_index}", value)
            for column_index, value in enumerate(row_values, start=1)
        )
        row_xml_parts.append(f'<row r="{row_index}">{cells_xml}</row>')
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
        '<sheets><sheet name="搜索结果" sheetId="1" r:id="rId1"/></sheets>'
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


def strip_markup(text: str) -> str:
    cleaned = TAG_RE.sub("", unescape(text or ""))
    return " ".join(cleaned.split())


def format_time(timestamp: int | str | None) -> str:
    if not timestamp:
        return ""
    try:
        dt = datetime.fromtimestamp(int(timestamp))
    except (TypeError, ValueError, OSError):
        return ""
    return (
        f"{dt.year:04d}年{dt.month:02d}月{dt.day:02d}日 "
        f"{dt.hour:02d}:{dt.minute:02d}:{dt.second:02d}"
    )


def join_tags(info: dict) -> str:
    names: list[str] = []
    for topic in info.get("topics", []):
        name = (topic or {}).get("name")
        if name and name not in names:
            names.append(name)
    for hashtag in info.get("hashtags", []):
        name = (hashtag or {}).get("name")
        if name and name not in names:
            names.append(name)
    return " | ".join(names)


def build_data_summary(info: dict) -> str:
    like_count = info.get("link_award_num", 0)
    comment_count = info.get("comment_num", 0)
    share_count = info.get("forward_num", 0)
    return f"点赞 {like_count} | 评论 {comment_count} | 分享 {share_count}"


def parse_detail_text(raw_text: str) -> str:
    if not raw_text:
        return ""

    try:
        parts = json.loads(raw_text)
    except json.JSONDecodeError:
        return strip_markup(raw_text)

    chunks: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        if part.get("type") != "text":
            continue
        text = strip_markup(part.get("text", ""))
        if text:
            chunks.append(text)
    return "\n".join(chunks)


def count_comment_items(comment_groups: list[dict]) -> int:
    total = 0
    for group in comment_groups or []:
        total += len(group.get("comment", []))
    return total


def flatten_comments(comment_groups: list[dict], max_comments: int) -> str:
    lines: list[str] = []
    counter = 1
    for group in comment_groups or []:
        for comment in group.get("comment", []):
            if counter > max_comments:
                return "\n".join(lines)
            user = (comment.get("user") or {}).get("username", "")
            text = strip_markup(comment.get("text", ""))
            if not text:
                continue
            reply_user = (comment.get("replyuser") or {}).get("username", "")
            prefix = f"{counter}. {user}"
            if reply_user:
                prefix += f" 回复 @{reply_user}"
            lines.append(f"{prefix}: {text}")
            counter += 1
    return "\n".join(lines)


def enrich_row_with_detail(client: XhhClient, row: dict, comment_limit: int) -> dict:
    link_id = row.get("_detail_link_id")
    h_src = row.get("_detail_h_src", "")
    if not link_id or not h_src:
        row["帖子详情"] = ""
        row["评论"] = ""
        return row

    detail_payload = client.link_tree(link_id=link_id, h_src=h_src, page=1, index=1, limit=20)
    result = detail_payload.get("result", {}) if isinstance(detail_payload, dict) else {}
    link = result.get("link", {}) if isinstance(result, dict) else {}
    comments = list(result.get("comments", []) if isinstance(result, dict) else [])
    total_page = int(result.get("total_page", 1) or 1) if isinstance(result, dict) else 1

    for page in range(2, total_page + 1):
        if count_comment_items(comments) >= comment_limit:
            break
        page_payload = client.link_tree(
            link_id=link_id,
            h_src=h_src,
            page=page,
            index=page,
            limit=20,
            is_first=0,
        )
        page_result = page_payload.get("result", {}) if isinstance(page_payload, dict) else {}
        comments.extend(page_result.get("comments", []) if isinstance(page_result, dict) else [])

    row["帖子详情"] = parse_detail_text(link.get("text", "")) or row.get("具体内容", "")
    row["评论"] = flatten_comments(comments, comment_limit)

    if link:
        row["网站链接"] = link.get("share_url") or row.get("网站链接", "")
        row["发布时间"] = format_time(link.get("create_at")) or row.get("发布时间", "")
        row["数据"] = build_data_summary(link)
        row["用户昵称"] = ((link.get("user") or {}).get("username")) or row.get("用户昵称", "")
        row["作品标题"] = strip_markup(link.get("title", "")) or row.get("作品标题", "")
        row["点赞数量"] = link.get("link_award_num", row.get("点赞数量", 0))
        row["评论数量"] = link.get("comment_num", row.get("评论数量", 0))
        row["分享数量"] = link.get("forward_num", row.get("分享数量", 0))
        row["用户ID"] = (link.get("user") or {}).get("userid", row.get("用户ID", ""))
        row["帖子ID"] = link.get("linkid") or row.get("帖子ID", "")
        row["标签"] = join_tags(link)
        row["更新时间"] = format_time(link.get("modify_at")) or row.get("更新时间", "")
        row["是否视频"] = "是" if link.get("has_video") else "否"

    return row


def enrich_search_rows(client: XhhClient, rows: list[dict], comment_limit: int) -> list[dict]:
    enriched_rows: list[dict] = []
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        print(f"fetch detail: {index}/{total} link_id={row.get('帖子ID', '')}")
        enriched_rows.append(enrich_row_with_detail(client, row, comment_limit))
    return enriched_rows


def normalize_search_item(item: dict) -> dict | None:
    if item.get("type") != "link":
        return None

    info = item.get("info", {})
    user = info.get("user", {})
    title = strip_markup(info.get("title", ""))
    description = strip_markup(info.get("description", ""))
    content_parts = [part for part in [title, description] if part]
    update_time = format_time(info.get("modify_at"))

    return {
        "平台": "小黑盒",
        "网站链接": info.get("share_url", ""),
        "发布时间": format_time(info.get("create_at")),
        "数据": build_data_summary(info),
        "用户昵称": user.get("username", ""),
        "具体内容": "\n".join(content_parts),
        "作品类型": "帖子",
        "作品标题": title,
        "点赞数量": info.get("link_award_num", 0),
        "评论数量": info.get("comment_num", 0),
        "分享数量": info.get("forward_num", 0),
        "用户ID": user.get("userid", ""),
        "帖子ID": info.get("linkid") or info.get("link_id") or "",
        "标签": join_tags(info),
        "更新时间": update_time,
        "是否视频": "是" if info.get("has_video") else "否",
        "帖子详情": "",
        "评论": "",
        "_detail_link_id": info.get("linkid") or info.get("link_id") or "",
        "_detail_h_src": info.get("h_src", ""),
    }


def normalize_search_payload(data: dict, params: dict[str, str]) -> dict:
    result = data.get("result", {})
    items = result.get("items", []) if isinstance(result, dict) else []
    normalized_items = [row for row in (normalize_search_item(item) for item in items) if row]
    return {
        "平台": "小黑盒",
        "接口": "general_search_v1",
        "关键词": params.get("q", ""),
        "结果数量": len(normalized_items),
        "结果": normalized_items,
    }


def http_get(url: str, headers: dict[str, str]) -> tuple[int, str, str]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        return response.status, response.headers.get("Content-Type", ""), body


def print_summary(route_name: str, data: dict) -> None:
    result = data.get("result")
    if route_name == "general_search_v1" and isinstance(result, dict):
        normalized = normalize_search_payload(data, {})
        items = normalized["结果"]
        print(f"items: {len(items)}")
        for row in items[:10]:
            print(f"- [{row['帖子ID']}] {row['用户昵称']} | {row['作品标题']}")
        return

    if isinstance(result, dict):
        print("result keys:", ", ".join(list(result.keys())[:12]))
    elif isinstance(result, list):
        print(f"result items: {len(result)}")
    else:
        print("result:", result)


def main() -> int:
    load_dotenv(ENV_PATH)
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print("Usage:")
        print("  python xhh_api.py <route> [key=value params]")
        print("  python xhh_api.py --search <关键词> [key=value params]")
        print("  python xhh_api.py general_search_v1 --query 模拟")
        print("")
        print("Examples:")
        print("  python xhh_api.py --search 模拟")
        print("  python xhh_api.py --search 模拟 limit=20 comment_limit=30")
        print("  python xhh_api.py general_search_v1 q=模拟")
        print("  python xhh_api.py related_recommend_web link_id=175495445 h_src=FxDNnklDNXqYrPXG7")
        print("")
        print("Env:")
        print("  XHH_SEARCH_LIMIT=10")
        print("  XHH_COMMENT_LIMIT=100")
        return 0

    if args[0] in {"--search", "-s"}:
        if len(args) < 2:
            print("missing search keyword", file=sys.stderr)
            return 1
        route_name = "general_search_v1"
        params = {"q": args[1], **parse_params(args[2:])}
    else:
        route_name = args[0]
        params = parse_params(args[1:])

    env_search_limit = getenv_int("XHH_SEARCH_LIMIT", DEFAULT_SEARCH_LIMIT)
    env_comment_limit = getenv_int("XHH_COMMENT_LIMIT", DEFAULT_COMMENT_LIMIT)

    if route_name == "general_search_v1":
        if "limit" not in params:
            params["limit"] = str(env_search_limit)
        comment_limit = pop_int_param(params, "comment_limit", env_comment_limit)
    else:
        comment_limit = env_comment_limit

    client = XhhClient()

    try:
        request_info = client.build_request(route_name, **params)
    except Exception as exc:
        print(f"bridge error: {exc}", file=sys.stderr)
        return 1

    print("=" * 60)
    print("xhh api python client")
    print("=" * 60)
    print("route:", request_info.route)
    print("path:", request_info.path)
    print("hkey:", request_info.hkey)
    print("timestamp:", request_info.timestamp)
    print("nonce:", request_info.nonce)
    print("url:", request_info.url)
    print("")

    try:
        status_code, content_type, body = http_get(request_info.url, request_info.headers)
    except Exception as exc:
        print(f"request error: {exc}", file=sys.stderr)
        return 1

    print(f"HTTP: {status_code}")
    print(f"content-type: {content_type}")
    print("")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        print(body[:4000])
        return 0

    print_summary(route_name, payload)
    print("")

    if route_name == "general_search_v1":
        normalized = normalize_search_payload(payload, params)
        normalized["结果"] = enrich_search_rows(client, normalized["结果"], comment_limit)
        output_path = build_output_path(route_name, ".xlsx")
        save_search_xlsx(normalized["结果"], output_path)
    else:
        output_path = build_output_path(route_name)
        save_json(payload, output_path)
    print(f"saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
