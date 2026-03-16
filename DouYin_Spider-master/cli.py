import argparse
import re
from datetime import datetime


SAVE_CHOICES = ["all", "media", "media-video", "media-image", "excel"]
SORT_TYPE_CHOICES = ["0", "1", "2"]
PUBLISH_TIME_CHOICES = ["0", "1", "7", "180"]
SEARCH_RANGE_CHOICES = ["0", "1", "2", "3"]
CONTENT_TYPE_CHOICES = ["0", "1", "2"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Standardized Douyin Spider CLI. Use this instead of editing main.py directly."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser("search", help="Search works by keyword")
    search_parser.add_argument("keyword", help="Search keyword")
    search_parser.add_argument("--num", type=int, default=20, help="Number of search results to fetch")
    search_parser.add_argument(
        "--save-choice",
        choices=SAVE_CHOICES,
        default="excel",
        help="Save mode. Default is excel to avoid unnecessary media downloads.",
    )
    search_parser.add_argument("--excel-name", default="", help="Excel filename without extension")
    search_parser.add_argument(
        "--sort-type",
        choices=SORT_TYPE_CHOICES,
        default="0",
        help="0 comprehensive, 1 most liked, 2 latest",
    )
    search_parser.add_argument(
        "--publish-time",
        choices=PUBLISH_TIME_CHOICES,
        default="0",
        help="0 unlimited, 1 one day, 7 one week, 180 half year",
    )
    search_parser.add_argument(
        "--filter-duration",
        default="",
        help='Video duration filter, e.g. "", "0-1", "1-5", "5-10000"',
    )
    search_parser.add_argument(
        "--search-range",
        choices=SEARCH_RANGE_CHOICES,
        default="0",
        help="0 all, 1 recently viewed, 2 not viewed, 3 following",
    )
    search_parser.add_argument(
        "--content-type",
        choices=CONTENT_TYPE_CHOICES,
        default="0",
        help="0 all, 1 video, 2 image-text",
    )

    user_parser = subparsers.add_parser("user", help="Fetch all works from a user")
    user_parser.add_argument("target", help="Douyin user homepage URL or sec_user_id")
    user_parser.add_argument(
        "--save-choice",
        choices=SAVE_CHOICES,
        default="excel",
        help="Save mode. Default is excel.",
    )
    user_parser.add_argument("--excel-name", default="", help="Excel filename without extension")

    work_parser = subparsers.add_parser("work", help="Fetch one or more work detail pages")
    work_parser.add_argument("targets", nargs="+", help="Work URLs")
    work_parser.add_argument(
        "--save-choice",
        choices=SAVE_CHOICES,
        default="excel",
        help="Save mode. Default is excel.",
    )
    work_parser.add_argument("--excel-name", default="", help="Excel filename without extension")

    live_parser = subparsers.add_parser("live", help="Listen to a Douyin live room")
    live_parser.add_argument("target", help="Live room ID or live room URL")

    refresh_cookie_parser = subparsers.add_parser(
        "refresh-cookie",
        help="Open Chrome to refresh DY_COOKIES or DY_LIVE_COOKIES after manual login/verification",
    )
    refresh_cookie_parser.add_argument(
        "--target",
        choices=["search", "www", "live"],
        default="search",
        help="search opens the search page to clear verification, www opens Douyin homepage, live opens Douyin live homepage",
    )
    refresh_cookie_parser.add_argument(
        "--keyword",
        default="榴莲",
        help="Keyword used when target=search",
    )

    return parser


def normalize_user_url(target: str) -> str:
    target = target.strip()
    if target.startswith(("http://", "https://")):
        match = re.search(r"/user/([^/?]+)", target)
        if not match:
            raise ValueError("User target must be a Douyin user homepage URL like https://www.douyin.com/user/<sec_user_id>")
        sec_user_id = match.group(1)
    else:
        sec_user_id = target
    return f"https://www.douyin.com/user/{sec_user_id}"


def normalize_live_id(target: str) -> str:
    target = target.strip()
    if target.startswith(("http://", "https://")):
        match = re.search(r"live\.douyin\.com/(\d+)", target)
        if not match:
            raise ValueError("Live target must be a live room URL like https://live.douyin.com/<room_id>")
        return match.group(1)
    return target


def default_excel_name(prefix: str) -> str:
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{now}"


def run_search(args: argparse.Namespace) -> None:
    from main import Data_Spider
    from utils.common_util import init

    auth, base_path = init()
    spider = Data_Spider()
    excel_name = args.excel_name or args.keyword
    spider.spider_some_search_work(
        auth=auth,
        query=args.keyword,
        require_num=args.num,
        base_path=base_path,
        save_choice=args.save_choice,
        sort_type=args.sort_type,
        publish_time=args.publish_time,
        filter_duration=args.filter_duration,
        search_range=args.search_range,
        content_type=args.content_type,
        excel_name=excel_name,
    )


def run_user(args: argparse.Namespace) -> None:
    from main import Data_Spider
    from utils.common_util import init

    auth, base_path = init()
    spider = Data_Spider()
    user_url = normalize_user_url(args.target)
    spider.spider_user_all_work(
        auth=auth,
        user_url=user_url,
        base_path=base_path,
        save_choice=args.save_choice,
        excel_name=args.excel_name,
    )


def run_work(args: argparse.Namespace) -> None:
    from main import Data_Spider
    from utils.common_util import init

    auth, base_path = init()
    spider = Data_Spider()
    excel_name = args.excel_name or default_excel_name("works")
    spider.spider_some_work(
        auth=auth,
        works=args.targets,
        base_path=base_path,
        save_choice=args.save_choice,
        excel_name=excel_name,
    )


def run_live(args: argparse.Namespace) -> None:
    from dy_live.server import DouyinLive
    import utils.common_util as common_util

    common_util.load_env()
    live_id = normalize_live_id(args.target)
    live = DouyinLive(live_id, common_util.dy_live_auth)
    live.start_ws()


def run_refresh_cookie(args: argparse.Namespace) -> None:
    from utils.cookie_util import refresh_cookie

    result = refresh_cookie(target=args.target, keyword=args.keyword)
    print(
        f"Updated {result['env_key']} from browser session. "
        f"title={result['title']!r}, url={result['url']}, cookie_count={result['cookie_count']}"
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "search":
            run_search(args)
        elif args.command == "user":
            run_user(args)
        elif args.command == "work":
            run_work(args)
        elif args.command == "live":
            run_live(args)
        elif args.command == "refresh-cookie":
            run_refresh_cookie(args)
        else:
            parser.error(f"Unknown command: {args.command}")
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
