#!/usr/bin/env python3

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from xhh_client import XhhClient


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"


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


def build_output_path(route_name: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"{route_name}_{timestamp}.json"


def save_json(payload: dict, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def http_get(url: str, headers: dict[str, str]) -> tuple[int, str, str]:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=30) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        body = response.read().decode(charset, errors="replace")
        return response.status, response.headers.get("Content-Type", ""), body


def print_summary(route_name: str, data: dict) -> None:
    result = data.get("result")
    if route_name == "general_search_v1" and isinstance(result, dict):
        items = result.get("items", [])
        print(f"items: {len(items)}")
        shown = 0
        for item in items:
            info = item.get("info", {})
            title = info.get("title") or ""
            link_id = info.get("linkid") or info.get("link_id") or ""
            item_type = item.get("type") or ""
            if not title:
                continue
            print(f"- [{item_type}] {link_id} {title}")
            shown += 1
            if shown >= 10:
                break
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

    output_path = build_output_path(route_name)
    save_json(payload, output_path)
    print(f"saved: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
