#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
NODE_BRIDGE = BASE_DIR / "JS" / "generate_request_json.js"


@dataclass
class RequestInfo:
    route: str
    path: str
    hkey: str
    timestamp: int
    nonce: str
    url: str
    headers: dict[str, str]
    params: dict[str, Any]


class XhhClient:
    def __init__(self, node_bridge: Path | None = None) -> None:
        self.node_bridge = node_bridge or NODE_BRIDGE

    def build_request(self, route_name: str, **params: Any) -> RequestInfo:
        payload = {
            "routeName": route_name,
            "customParams": {key: str(value) for key, value in params.items()},
        }
        command = ["node", str(self.node_bridge), "--stdin-json"]
        completed = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        output = completed.stdout.strip() or completed.stderr.strip()
        if not output:
            raise RuntimeError("node bridge returned empty output")

        try:
            result = json.loads(output)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"invalid json from node bridge: {output}") from exc

        if completed.returncode != 0 or not result.get("ok"):
            raise RuntimeError(result.get("error", "node bridge failed"))

        return RequestInfo(
            route=result["route"],
            path=result["path"],
            hkey=result["hkey"],
            timestamp=result["timestamp"],
            nonce=result["nonce"],
            url=result["url"],
            headers=result["headers"],
            params=result.get("params", {}),
        )

    def get_json(self, route_name: str, **params: Any) -> dict[str, Any]:
        request_info = self.build_request(route_name, **params)
        request = urllib.request.Request(request_info.url, headers=request_info.headers, method="GET")

        with urllib.request.urlopen(request, timeout=30) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            body = response.read().decode(charset, errors="replace")
            return json.loads(body)

    def search(self, query: str, **params: Any) -> dict[str, Any]:
        merged = {
            "q": query,
            **params,
        }
        return self.get_json("general_search_v1", **merged)

    def link_tree(
        self,
        link_id: str | int,
        h_src: str,
        page: int = 1,
        index: int | None = None,
        limit: int = 20,
        is_first: int = 1,
        owner_only: int = 0,
    ) -> dict[str, Any]:
        merged = {
            "link_id": link_id,
            "h_src": h_src,
            "page": page,
            "index": index if index is not None else page,
            "limit": limit,
            "is_first": is_first,
            "owner_only": owner_only,
        }
        return self.get_json("link_tree", **merged)

    def related_recommend(self, link_id: str | int, h_src: str) -> dict[str, Any]:
        return self.get_json("related_recommend_web", link_id=link_id, h_src=h_src)
