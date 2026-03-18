#!/usr/bin/env python3

from __future__ import annotations

import json
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
TAG_RE = re.compile(r"<[^>]+>")
SEARCH_HEADERS = [
    "平台",
    "网站链接",
    "发布时间",
    "数据",
    "用户昵称",
    "具体内容",
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
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print("Usage:")
        print("  python xhh_api.py <route> [key=value params]")
        print("  python xhh_api.py --search <关键词> [key=value params]")
        print("  python xhh_api.py general_search_v1 --query 模拟")
        print("")
        print("Examples:")
        print("  python xhh_api.py --search 模拟")
        print("  python xhh_api.py general_search_v1 q=模拟")
        print("  python xhh_api.py related_recommend_web link_id=175495445 h_src=FxDNnklDNXqYrPXG7")
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
        output_path = build_output_path(route_name, ".xlsx")
        save_search_xlsx(normalized["结果"], output_path)
    else:
        output_path = build_output_path(route_name)
        save_json(payload, output_path)
    print(f"saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
