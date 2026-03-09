#!/usr/bin/env python
import argparse
import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.sse import sse_client


async def call_tool(url: str, tool: str, args_obj: dict) -> int:
    async with sse_client(url) as streams:
        read_stream, write_stream = streams
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool, args_obj)

    output_parts = []
    for item in result.content:
        text = getattr(item, "text", None)
        if text:
            output_parts.append(text)

    if output_parts:
        print("\n".join(output_parts))
    else:
        print(json.dumps({"ok": True, "message": "Tool returned no text content"}, ensure_ascii=False))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Call an MCP tool over SSE")
    parser.add_argument("--url", default="http://127.0.0.1:9000/sse", help="MCP SSE URL")
    parser.add_argument("--tool", required=True, help="Tool name")
    parser.add_argument(
        "--args",
        default="{}",
        help='Tool arguments as JSON string, e.g. "{\"people_count\":4}"',
    )
    parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help="Single argument in key=value format. Can be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    ns = parse_args()
    if ns.arg:
        args_obj = {}
        for item in ns.arg:
            if "=" not in item:
                print(f"Invalid --arg value: {item}. Expected key=value", file=sys.stderr)
                return 2
            key, value = item.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                print(f"Invalid --arg key in: {item}", file=sys.stderr)
                return 2
            # Try to parse typed values: numbers, booleans, null, arrays, objects.
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                parsed_value = value
            args_obj[key] = parsed_value
    else:
        raw_args = ns.args
        candidates = [
            raw_args,
            raw_args.strip("'"),
            raw_args.strip('"'),
            raw_args.replace('\\"', '"'),
            raw_args.strip("'").replace('\\"', '"'),
            raw_args.strip('"').replace('\\"', '"'),
        ]

        args_obj = None
        last_error = None
        for candidate in candidates:
            try:
                args_obj = json.loads(candidate)
                break
            except json.JSONDecodeError as exc:
                last_error = exc

        if args_obj is None:
            print(f"Invalid --args JSON: {last_error}", file=sys.stderr)
            return 2

    if not isinstance(args_obj, dict):
        print("--args must decode to a JSON object", file=sys.stderr)
        return 2

    try:
        return asyncio.run(call_tool(ns.url, ns.tool, args_obj))
    except Exception as exc:
        print(f"MCP call failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
