import argparse
import json
import re
import time
from pathlib import Path

import openpyxl
from bilibili_api import Credential, search, sync


DEFAULT_PAGE_SIZE = 20
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
COOKIE_PATH = Path(__file__).resolve().parent / "cookie.json"
ORDER_MAP = {
    "totalrank": search.OrderVideo.TOTALRANK,
    "click": search.OrderVideo.CLICK,
    "pubdate": search.OrderVideo.PUBDATE,
    "dm": search.OrderVideo.DM,
    "stow": search.OrderVideo.STOW,
    "scores": search.OrderVideo.SCORES,
}
EXPORT_PRIORITY_FIELDS = [
    "platform",
    "website_link",
    "publish_time_display",
    "data_summary",
    "nickname",
    "content_preview",
]
EXPORT_FIELD_LABELS = {
    "platform": "平台",
    "website_link": "网站链接",
    "publish_time_display": "发布时间",
    "data_summary": "数据",
    "nickname": "用户昵称",
    "content_preview": "具体内容",
    "work_type": "作品类型",
    "title": "作品标题",
    "play_count": "播放数量",
    "danmaku_count": "弹幕数量",
    "comment_count": "评论数量",
    "collect_count": "收藏数量",
    "digg_count": "点赞数量",
    "video_duration": "时长",
    "topics": "标签",
    "video_cover": "视频封面url",
    "user_url": "用户主页url",
    "user_id": "用户id",
    "user_desc": "用户简介",
    "author_avatar": "头像url",
    "aid": "aid",
    "bvid": "bvid",
    "category_name": "分区",
    "rank_index": "搜索排名",
}


def strip_html(text):
    text = str(text or "")
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", " ", text).strip()


def norm_text(text):
    illegal_characters = re.compile(r"[\000-\010]|[\013-\014]|[\016-\037]")
    return illegal_characters.sub("", str(text))


def timestamp_to_cn_str(timestamp):
    time_local = time.localtime(int(timestamp))
    return (
        f"{time_local.tm_year}年{time_local.tm_mon}月{time_local.tm_mday}日 "
        f"{time_local.tm_hour:02d}:{time_local.tm_min:02d}:{time_local.tm_sec:02d}"
    )


def build_data_summary(item):
    parts = [
        f"播放{item.get('play_count', 0)}",
        f"弹幕{item.get('danmaku_count', 0)}",
        f"评论{item.get('comment_count', 0)}",
        f"收藏{item.get('collect_count', 0)}",
        f"点赞{item.get('digg_count', 0)}",
    ]
    coin_count = item.get("coin_count")
    if coin_count not in (None, "", "未知"):
        parts.append(f"投币{coin_count}")
    return " | ".join(parts)


def build_content_preview(item, limit=120):
    content = item.get("desc") or item.get("title") or ""
    content = strip_html(content)
    if len(content) <= limit:
        return content
    return content[:limit].rstrip() + "..."


def prepare_export_row(item):
    row = {
        "platform": "b站",
        "website_link": item.get("work_url", ""),
        "publish_time_display": timestamp_to_cn_str(item.get("create_time", 0)) if item.get("create_time") else "",
        "data_summary": build_data_summary(item),
        "nickname": item.get("nickname", ""),
        "content_preview": build_content_preview(item),
    }
    for key, value in item.items():
        if key in {"work_url", "create_time", "nickname", "desc"}:
            continue
        row[key] = value
    return row


def get_headers(field_order):
    return [EXPORT_FIELD_LABELS.get(field, field) for field in field_order]


def save_to_xlsx(rows, file_path):
    export_rows = [prepare_export_row(row) for row in rows]
    field_order = list(EXPORT_PRIORITY_FIELDS)
    if export_rows:
        field_order.extend([field for field in export_rows[0].keys() if field not in EXPORT_PRIORITY_FIELDS])
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(get_headers(field_order))
    for row in export_rows:
        worksheet.append([norm_text(row.get(field, "")) for field in field_order])
    workbook.save(file_path)


def load_cookie_items(cookie_path):
    return json.loads(Path(cookie_path).read_text(encoding="utf-8"))


def build_credential(cookie_items):
    cookie_map = {item["name"]: item["value"] for item in cookie_items if item.get("name")}
    return Credential(
        sessdata=cookie_map.get("SESSDATA"),
        bili_jct=cookie_map.get("bili_jct"),
        buvid3=cookie_map.get("buvid3"),
        buvid4=cookie_map.get("buvid4"),
        dedeuserid=cookie_map.get("DedeUserID"),
        ac_time_value=cookie_map.get("ac_time_value"),
    )


def fetch_search_page(
    keyword,
    page,
    page_size,
    order,
    time_range=-1,
    video_zone_type=None,
    order_sort=None,
    time_start=None,
    time_end=None,
):
    return sync(
        search.search_by_type(
            keyword=keyword,
            search_type=search.SearchObjectType.VIDEO,
            order_type=ORDER_MAP[order],
            time_range=time_range,
            video_zone_type=video_zone_type,
            order_sort=order_sort,
            time_start=time_start,
            time_end=time_end,
            page=page,
            page_size=page_size,
        )
    )


def transform_video_item(item):
    bvid = item.get("bvid", "")
    mid = item.get("mid", "")
    return {
        "work_type": "视频",
        "work_url": f"https://www.bilibili.com/video/{bvid}" if bvid else item.get("arcurl", ""),
        "title": strip_html(item.get("title", "")),
        "desc": strip_html(item.get("description", "")),
        "play_count": item.get("play", 0),
        "danmaku_count": item.get("video_review", item.get("danmaku", 0)),
        "comment_count": item.get("review", 0),
        "collect_count": item.get("favorites", 0),
        "digg_count": item.get("like", 0),
        "video_duration": item.get("duration", ""),
        "topics": strip_html(item.get("tag", "")),
        "create_time": item.get("pubdate", 0),
        "video_cover": ("https:" + item["pic"]) if str(item.get("pic", "")).startswith("//") else item.get("pic", ""),
        "user_url": f"https://space.bilibili.com/{mid}" if mid else "",
        "user_id": mid,
        "nickname": item.get("author", ""),
        "user_desc": "",
        "author_avatar": item.get("upic", "") or item.get("uface", ""),
        "aid": item.get("aid", ""),
        "bvid": bvid,
        "category_name": item.get("typename", ""),
        "rank_index": item.get("rank_index", ""),
    }


def search_videos(keyword, num, page_size, order, time_range=-1, video_zone_type=None, order_sort=None, time_start=None, time_end=None):
    results = []
    page = 1
    while len(results) < num:
        data = fetch_search_page(
            keyword=keyword,
            page=page,
            page_size=page_size,
            order=order,
            time_range=time_range,
            video_zone_type=video_zone_type,
            order_sort=order_sort,
            time_start=time_start,
            time_end=time_end,
        )
        page_items = data.get("result") or []
        if not page_items:
            break
        for item in page_items:
            if item.get("type") != "video":
                continue
            results.append(transform_video_item(item))
            if len(results) >= num:
                break
        total_pages = data.get("numPages", page)
        if page >= total_pages:
            break
        page += 1
    return results[:num]


def build_parser():
    parser = argparse.ArgumentParser(description="Search bilibili videos with bilibili_api and export to Excel.")
    parser.add_argument("keyword", help="Search keyword")
    parser.add_argument("--num", type=int, default=20, help="Number of videos to fetch")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE, help="Search page size")
    parser.add_argument("--order", choices=list(ORDER_MAP.keys()), default="totalrank", help="Search order")
    parser.add_argument(
        "--time-range",
        type=int,
        default=-1,
        help="Video duration filter in minutes bucket. <=10 means 10分钟以下, <=30 means 10-30分钟, <=60 means 30-60分钟, >60 means 60分钟以上.",
    )
    parser.add_argument("--video-zone-type", type=int, default=None, help="Video zone tid filter")
    parser.add_argument("--order-sort", type=int, choices=[0, 1], default=None, help="Sort direction, 0 desc, 1 asc")
    parser.add_argument("--time-start", default=None, help='Start date, format: YYYY-MM-DD')
    parser.add_argument("--time-end", default=None, help='End date, format: YYYY-MM-DD')
    parser.add_argument("--excel-name", default="", help="Excel filename without extension")
    parser.add_argument("--cookie-path", default=str(COOKIE_PATH), help="Path to bilibili cookie.json")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    cookie_items = load_cookie_items(args.cookie_path)
    credential = build_credential(cookie_items)
    if not credential.sessdata:
        raise SystemExit("cookie.json is missing SESSDATA")
    if bool(args.time_start) != bool(args.time_end):
        raise SystemExit("--time-start and --time-end must be used together")

    rows = search_videos(
        keyword=args.keyword,
        num=args.num,
        page_size=args.page_size,
        order=args.order,
        time_range=args.time_range,
        video_zone_type=args.video_zone_type,
        order_sort=args.order_sort,
        time_start=args.time_start,
        time_end=args.time_end,
    )
    if not rows:
        raise SystemExit(f"No bilibili video results for keyword: {args.keyword}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    excel_name = args.excel_name or args.keyword
    file_path = OUTPUT_DIR / f"{excel_name}.xlsx"
    save_to_xlsx(rows, file_path)
    print(f"Saved {len(rows)} bilibili results to {file_path}")


if __name__ == "__main__":
    main()
