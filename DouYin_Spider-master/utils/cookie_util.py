import asyncio
from pathlib import Path
from urllib.parse import quote, parse_qs, urlparse

from playwright.async_api import async_playwright


webid = None
search_request_params = {}


def handle_request(request):
    url = request.url
    global search_request_params
    if url.startswith('https://www.douyin.com/aweme/v1/web/user/profile/other/'):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        global webid
        webid = query_params.get('webid', [None])[0]
    elif url.startswith('https://www.douyin.com/aweme/v1/web/general/search/'):
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        search_request_params = {
            'webid': query_params.get('webid', [None])[0],
            'msToken': query_params.get('msToken', [None])[0],
            'uifid': query_params.get('uifid', [None])[0],
        }


def build_cookie_str(page_cookies, domain_keyword="douyin.com"):
    pairs = []
    seen_names = set()
    for cookie in page_cookies:
        domain = cookie.get("domain", "")
        name = cookie.get("name")
        value = cookie.get("value", "")
        if domain_keyword not in domain or not name or name in seen_names:
            continue
        seen_names.add(name)
        pairs.append(f"{name}={value}")
    return "; ".join(pairs)


async def open_page_and_collect(url: str, headless: bool = False):
    global webid
    global search_request_params
    webid = None
    search_request_params = {}
    print("将打开 Chrome。请在浏览器中完成登录或验证码，然后回到终端按回车继续。")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
            ],
            channel='chrome'
        )
        page = await browser.new_page()
        page.on("request", lambda request: handle_request(request=request))
        await page.goto(url)
        await page.wait_for_timeout(3000)
        await asyncio.to_thread(input, "完成登录/验证后按回车继续...")
        page_cookies = await page.context.cookies()
        current_url = page.url
        page_title = await page.title()
        await browser.close()
    return {
        "url": current_url,
        "title": page_title,
        "webid": webid,
        "search_request_params": search_request_params,
        "cookies": page_cookies,
        "cookie_str": build_cookie_str(page_cookies),
    }


def save_cookie_to_env(env_key: str, cookie_str: str, env_path: str = ".env"):
    path = Path(env_path)
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    updated = False
    for index, line in enumerate(lines):
        if line.startswith(f"{env_key}="):
            lines[index] = f"{env_key}={cookie_str}"
            updated = True
            break
    if not updated:
        lines.append(f"{env_key}={cookie_str}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def refresh_cookie(target: str = "search", keyword: str = "榴莲", headless: bool = False):
    if target == "search":
        url = f'https://www.douyin.com/search/{quote(keyword)}?type=general'
        env_key = "DY_COOKIES"
    elif target == "www":
        url = 'https://www.douyin.com/'
        env_key = "DY_COOKIES"
    elif target == "live":
        url = 'https://live.douyin.com/'
        env_key = "DY_LIVE_COOKIES"
    else:
        raise ValueError(f"Unsupported target: {target}")

    result = asyncio.run(open_page_and_collect(url, headless=headless))
    if not result["cookie_str"]:
        raise RuntimeError("No Douyin cookies were collected from the browser session.")
    save_cookie_to_env(env_key, result["cookie_str"])
    if target == "search":
        if result["search_request_params"].get("webid"):
            save_cookie_to_env("DY_SEARCH_WEBID", result["search_request_params"]["webid"])
        if result["search_request_params"].get("msToken"):
            save_cookie_to_env("DY_SEARCH_MSTOKEN", result["search_request_params"]["msToken"])
    return {
        "target": target,
        "env_key": env_key,
        "url": result["url"],
        "title": result["title"],
        "cookie_count": len(result["cookies"]),
        "webid": result["webid"],
        "search_request_params": result["search_request_params"],
    }


def get_new_cookies():
    result = refresh_cookie("www")
    return result


if __name__ == '__main__':
    print(refresh_cookie("www"))
