# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler/blob/main/media_platform/tieba/login.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


import asyncio
import functools
import json
import sys
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page
from tenacity import (RetryError, retry, retry_if_result, stop_after_attempt,
                      wait_fixed)

import config
from base.base_crawler import AbstractLogin
from tools import utils


class BaiduTieBaLogin(AbstractLogin):
    @staticmethod
    def _normalize_same_site(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        normalized = str(value).strip().lower()
        if normalized in {"none", "no_restriction"}:
            return "None"
        if normalized == "lax":
            return "Lax"
        if normalized == "strict":
            return "Strict"
        return None

    @classmethod
    def _build_playwright_cookie(cls, raw_cookie: dict) -> Optional[dict]:
        name = str(raw_cookie.get("name") or "").strip()
        if not name:
            return None

        value = str(raw_cookie.get("value") or "")
        domain = str(raw_cookie.get("domain") or "").strip()
        path = str(raw_cookie.get("path") or "/")
        secure = bool(raw_cookie.get("secure", False))
        host_only = bool(raw_cookie.get("hostOnly", False))

        cookie = {
            "name": name,
            "value": value,
            "path": path,
            "secure": secure,
            "httpOnly": bool(raw_cookie.get("httpOnly", False)),
        }

        same_site = cls._normalize_same_site(raw_cookie.get("sameSite"))
        if same_site:
            cookie["sameSite"] = same_site

        expires = raw_cookie.get("expirationDate")
        if expires not in (None, "", 0):
            try:
                cookie["expires"] = float(expires)
            except (TypeError, ValueError):
                pass

        if host_only and domain:
            scheme = "https" if secure else "http"
            cookie["url"] = f"{scheme}://{domain}{path}"
        else:
            cookie["domain"] = domain or ".baidu.com"

        return cookie

    @classmethod
    def _load_cookie_file(cls, cookie_path: Path) -> list[dict]:
        raw_text = cookie_path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        if not isinstance(payload, list):
            raise ValueError("cookie json file must contain a JSON array")

        cookies: list[dict] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            cookie = cls._build_playwright_cookie(item)
            if cookie:
                cookies.append(cookie)
        return cookies

    @classmethod
    def _load_cookies_for_context(cls, cookie_str: str) -> list[dict]:
        cookie_str = (cookie_str or "").strip()
        if not cookie_str:
            return []

        cookie_path = Path(cookie_str).expanduser()
        if cookie_path.is_file():
            utils.logger.info(
                f"[BaiduTieBaLogin.login_by_cookies] Loading cookies from file: {cookie_path}"
            )
            return cls._load_cookie_file(cookie_path)

        cookies: list[dict] = []
        for key, value in utils.convert_str_cookie_to_dict(cookie_str).items():
            cookies.append(
                {
                    "name": key,
                    "value": value,
                    "domain": ".baidu.com",
                    "path": "/",
                }
            )
        return cookies

    def __init__(self,
                 login_type: str,
                 browser_context: BrowserContext,
                 context_page: Page,
                 login_phone: Optional[str] = "",
                 cookie_str: str = ""
                 ):
        config.LOGIN_TYPE = login_type
        self.browser_context = browser_context
        self.context_page = context_page
        self.login_phone = login_phone
        self.cookie_str = cookie_str

    @retry(stop=stop_after_attempt(600), wait=wait_fixed(1), retry=retry_if_result(lambda value: value is False))
    async def check_login_state(self) -> bool:
        """
        Poll to check if login status is successful, return True if successful, otherwise return False

        Returns:

        """
        current_cookie = await self.browser_context.cookies()
        _, cookie_dict = utils.convert_cookies(current_cookie)
        stoken = cookie_dict.get("STOKEN")
        ptoken = cookie_dict.get("PTOKEN")
        if stoken or ptoken:
            return True
        return False

    async def begin(self):
        """Start login baidutieba"""
        utils.logger.info("[BaiduTieBaLogin.begin] Begin login baidutieba ...")
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        else:
            raise ValueError("[BaiduTieBaLogin.begin]Invalid Login Type Currently only supported qrcode or phone or cookies ...")

    async def login_by_mobile(self):
        """Login baidutieba by mobile"""
        pass

    async def login_by_qrcode(self):
        """login baidutieba website and keep webdriver login state"""
        utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] Begin login baidutieba by qrcode ...")
        qrcode_img_selector = "xpath=//img[@class='tang-pass-qrcode-img']"
        # find login qrcode
        base64_qrcode_img = await utils.find_login_qrcode(
            self.context_page,
            selector=qrcode_img_selector
        )
        if not base64_qrcode_img:
            utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
            # if this website does not automatically popup login dialog box, we will manual click login button
            await asyncio.sleep(0.5)
            login_button_ele = self.context_page.locator("xpath=//li[@class='u_login']")
            await login_button_ele.click()
            base64_qrcode_img = await utils.find_login_qrcode(
                self.context_page,
                selector=qrcode_img_selector
            )
            if not base64_qrcode_img:
                utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] login failed , have not found qrcode please check ....")
                sys.exit()

        # show login qrcode
        # fix issue #12
        # we need to use partial function to call show_qrcode function and run in executor
        # then current asyncio event loop will not be blocked
        partial_show_qrcode = functools.partial(utils.show_qrcode, base64_qrcode_img)
        asyncio.get_running_loop().run_in_executor(executor=None, func=partial_show_qrcode)

        utils.logger.info(f"[BaiduTieBaLogin.login_by_qrcode] waiting for scan code login, remaining time is 120s")
        try:
            await self.check_login_state()
        except RetryError:
            utils.logger.info("[BaiduTieBaLogin.login_by_qrcode] Login baidutieba failed by qrcode login method ...")
            sys.exit()

        wait_redirect_seconds = 5
        utils.logger.info(f"[BaiduTieBaLogin.login_by_qrcode] Login successful then wait for {wait_redirect_seconds} seconds redirect ...")
        await asyncio.sleep(wait_redirect_seconds)

    async def login_by_cookies(self):
        """login baidutieba website by cookies"""
        utils.logger.info("[BaiduTieBaLogin.login_by_cookies] Begin login baidutieba by cookie ...")
        cookies = self._load_cookies_for_context(self.cookie_str)
        if not cookies:
            utils.logger.warning("[BaiduTieBaLogin.login_by_cookies] Cookie input is empty, skipping cookie injection")
            return

        await self.browser_context.add_cookies(cookies)
        utils.logger.info(
            f"[BaiduTieBaLogin.login_by_cookies] Injected {len(cookies)} cookies into browser context"
        )
