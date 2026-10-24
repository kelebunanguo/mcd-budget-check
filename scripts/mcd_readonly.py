#!/usr/bin/env python3
"""Narrow, read-only McDonald's MCP client using the official SDK."""

import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
import sys

ENDPOINT = "https://mcp.mcd.cn"
ALLOWED_TOOLS = frozenset({
    "now-time-info", "query-nearby-stores", "delivery-query-addresses",
    "delivery-query-stores", "query-meals", "query-meal-detail",
    "query-store-coupons", "calculate-price", "list-nutrition-foods",
})


def read_token(env_file=None):
    token = os.environ.get("MCD_MCP_TOKEN", "").strip()
    if not token and env_file:
        for line in Path(env_file).read_text(encoding="utf-8").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key == "MCD_MCP_TOKEN":
                token = value.strip().strip("\"'")
                break
    if not token or token.startswith("${") or any(c.isspace() for c in token):
        raise ValueError("请设置有效的本地 MCD_MCP_TOKEN；不要在命令参数中传入 Token。")
    return token


def business_payload(result):
    """Unwrap only an unambiguous business object; preserve other MCP content."""
    if result.get("isError"):
        return None
    structured = result.get("structuredContent")
    if isinstance(structured, dict) and "success" in structured:
        return structured
    found = []
    for block in result.get("content", []):
        if block.get("type") != "text":
            continue
        try:
            item = json.loads(block.get("text", ""))
        except (ValueError, TypeError):
            continue
        if isinstance(item, dict) and "success" in item:
            found.append(item)
    return found[0] if len(found) == 1 else None


async def invoke(command, token, tool=None, arguments=None):
    if command == "call" and tool not in ALLOWED_TOOLS:
        raise ValueError("此 Skill 仅允许查询与计价，禁止调用此工具。")
    import httpx2
    from mcp import Client
    from mcp.client.streamable_http import streamable_http_client

    async with httpx2.AsyncClient(
        headers={"Authorization": f"Bearer {token}"},
        timeout=httpx2.Timeout(30, read=45),
    ) as http:
        async with Client(streamable_http_client(ENDPOINT, http_client=http)) as client:
            tools = []
            cursor = None
            while True:
                page = await client.list_tools(cursor=cursor)
                tools.extend(page.tools)
                cursor = page.next_cursor
                if not cursor:
                    break
            permitted = {t.name: t for t in tools if t.name in ALLOWED_TOOLS}
            if command == "tools":
                return {"endpoint": ENDPOINT, "server_tool_count": len(tools),
                        "tools": [t.model_dump(mode="json", by_alias=True)
                                  for t in permitted.values()]}
            if tool not in permitted:
                raise ValueError("官方服务当前未提供该工具。")
            import jsonschema
            jsonschema.validate(arguments, permitted[tool].input_schema)
            result = await client.call_tool(tool, arguments=arguments)
            raw = result.model_dump(mode="json", by_alias=True)
            payload = business_payload(raw)
            return {"tool": tool, "arguments": arguments,
                    "business": payload, "mcp_result": raw}


def private_write(path, value):
    destination = Path(path)
    with os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600),
                   "w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", help="仅从此本地文件读取 MCD_MCP_TOKEN")
    parser.add_argument("--out", help="私有 JSON 输出路径，不能已存在")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("tools")
    call = sub.add_parser("call")
    call.add_argument("tool", choices=sorted(ALLOWED_TOOLS))
    call.add_argument("--args-file", required=True, help="JSON 参数对象文件")
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)
    try:
        arguments = None
        if args.command == "call":
            arguments = json.loads(Path(args.args_file).read_text(encoding="utf-8"))
            if not isinstance(arguments, dict):
                raise ValueError("参数文件必须是 JSON 对象。")
        token = read_token(args.env_file)
        result = asyncio.run(invoke(args.command, token, getattr(args, "tool", None), arguments))
        if args.out:
            private_write(args.out, result)
            print("已将结果写入指定本地文件。")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        if result.get("mcp_result", {}).get("isError"):
            return 2
        payload = result.get("business")
        if args.command == "call" and args.tool == "calculate-price" and payload is None:
            return 2
        if payload is not None and (payload.get("success") is not True or payload.get("code") != 200):
            return 2
        return 0
    except (OSError, ValueError, ImportError) as error:
        print(f"本地配置、输入或依赖检查失败（{type(error).__name__}）。请检查文件及安装说明。", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"MCP 请求未完成（{type(error).__name__}）。请检查网络、Token 或服务状态；尚未获得有效报价。", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
