"""MCP Server for L.O.G.O.S. (FastMCP when available + zero-dependency stdio JSON-RPC 2.0)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .session import LogosSession

TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "logos_ingest_turn",
        "description": "Ingest a turn into L.O.G.O.S., auto-crystallizing older episodes into RYTT glyphs on overflow.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "default": "user"},
                "content": {"type": "string"},
                "epistemic_tier": {"type": "string", "enum": ["D", "P", "O", "F"], "default": "P"},
                "anti_reason": {"type": "string", "default": ""},
            },
            "required": ["content"],
        },
    },
    {
        "name": "logos_compose_viewport",
        "description": "Compose the Dynamic LOD Viewport with Layer-3 Bloom MMU auto-prefetch and active truth mask.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_tokens": {"type": "integer"},
                "zoom_glyph_ids": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["query"],
        },
    },
    {
        "name": "logos_hydrate_glyph",
        "description": "Dereference a pinned TensorGlyph back to SHA-256 verified verbatim source text.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "glyph_id": {"type": "string"},
                "query": {"type": "string", "default": ""},
                "max_chars": {"type": "integer", "default": 2000},
            },
            "required": ["glyph_id"],
        },
    },
    {
        "name": "logos_register_anti_glyph",
        "description": "Quarantine a disproven hypothesis or dead-end branch as an Anti-Glyph.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string"},
                "reason": {"type": "string"},
            },
            "required": ["content", "reason"],
        },
    },
    {
        "name": "logos_status",
        "description": "Inspect current RYTT frontier notation, bitemporal truth slots, KV stats, and Merkle integrity.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "logos_export_cartridge",
        "description": "Export a portable SHA-256 verified .logos session cartridge.",
        "inputSchema": {
            "type": "object",
            "properties": {"output_path": {"type": "string"}},
            "required": ["output_path"],
        },
    },
]


def _dispatch_tool(session: LogosSession, name: str, args: Dict[str, Any]) -> str:
    if name == "logos_ingest_turn":
        res = session.ingest(
            role=str(args.get("role", "user")),
            content=str(args["content"]),
            epistemic_tier=str(args.get("epistemic_tier", "P")),
            anti_reason=str(args.get("anti_reason", "")),
        )
        return json.dumps(res, ensure_ascii=False)

    if name == "logos_compose_viewport":
        frame = session.compose(
            query=str(args["query"]),
            max_tokens=int(args["max_tokens"]) if args.get("max_tokens") is not None else None,
            zoom_glyph_ids=tuple(args.get("zoom_glyph_ids") or ()),
        )
        return json.dumps(
            {
                "frontier_notation": frame.frontier_notation,
                "total_tokens": frame.total_tokens,
                "budget_tokens": frame.budget_tokens,
                "virtual_tokens_covered": frame.virtual_tokens_covered,
                "compression_ratio": round(frame.compression_ratio, 2),
                "bloom_hits": [
                    {"glyph_id": h.glyph_id, "entities": list(h.matched_entities)}
                    for h in frame.bloom_hits
                ],
                "rendered_text": frame.rendered_text,
            },
            ensure_ascii=False,
        )

    if name == "logos_hydrate_glyph":
        sl = session.hydrate(
            glyph_id=str(args["glyph_id"]),
            query=str(args.get("query", "")),
            max_chars=int(args.get("max_chars", 2000)),
        )
        return json.dumps(
            {
                "glyph_id": sl.glyph_id,
                "raw_sha256": sl.raw_sha256,
                "verified_sha256": sl.verified_sha256,
                "token_count": sl.token_count,
                "content": sl.content,
            },
            ensure_ascii=False,
        )

    if name == "logos_register_anti_glyph":
        res = session.register_anti_glyph(
            content=str(args["content"]),
            reason=str(args["reason"]),
        )
        return json.dumps(res, ensure_ascii=False)

    if name == "logos_status":
        return json.dumps(session.status(), ensure_ascii=False)

    if name == "logos_export_cartridge":
        out = session.export_cartridge(Path(str(args["output_path"])))
        return json.dumps({"cartridge_path": str(out), "valid": True}, ensure_ascii=False)

    raise ValueError(f"Unknown tool: {name!r}")


def handle_jsonrpc_message(msg: Dict[str, Any], session: LogosSession) -> Optional[Dict[str, Any]]:
    """Pure JSON-RPC 2.0 dispatcher for stdio MCP transport."""
    req_id = msg.get("id")
    method = str(msg.get("method", ""))
    params = msg.get("params") or {}

    if req_id is None:
        # JSON-RPC notification (e.g. notifications/initialized): no response
        return None

    try:
        if method == "initialize":
            result: Dict[str, Any] = {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "logos-mcp", "version": "0.1.0"},
                "capabilities": {"tools": {"listChanged": False}},
            }
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOL_DEFINITIONS}
        elif method == "tools/call":
            tool_name = str(params.get("name", ""))
            tool_args = dict(params.get("arguments") or {})
            text = _dispatch_tool(session, tool_name, tool_args)
            result = {"content": [{"type": "text", "text": text}], "isError": False}
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        return {"jsonrpc": "2.0", "id": req_id, "result": result}
    except Exception as exc:  # fail-closed tool execution reporting
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": f"ERROR: {exc}"}],
                "isError": True,
            },
        }


def serve_jsonrpc_stdio(session: LogosSession) -> int:
    """Line-delimited JSON-RPC 2.0 loop over stdin/stdout."""
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()
            continue

        resp = handle_jsonrpc_message(msg, session)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


def serve_fastmcp_if_available(session: LogosSession) -> Optional[int]:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except ImportError:
        return None

    server = FastMCP("logos")

    @server.tool()
    def logos_ingest_turn(
        content: str,
        role: str = "user",
        epistemic_tier: str = "P",
        anti_reason: str = "",
    ) -> str:
        return _dispatch_tool(
            session,
            "logos_ingest_turn",
            {
                "content": content,
                "role": role,
                "epistemic_tier": epistemic_tier,
                "anti_reason": anti_reason,
            },
        )

    @server.tool()
    def logos_compose_viewport(
        query: str,
        max_tokens: Optional[int] = None,
        zoom_glyph_ids: Optional[List[str]] = None,
    ) -> str:
        return _dispatch_tool(
            session,
            "logos_compose_viewport",
            {"query": query, "max_tokens": max_tokens, "zoom_glyph_ids": zoom_glyph_ids or []},
        )

    @server.tool()
    def logos_hydrate_glyph(glyph_id: str, query: str = "", max_chars: int = 2000) -> str:
        return _dispatch_tool(
            session,
            "logos_hydrate_glyph",
            {"glyph_id": glyph_id, "query": query, "max_chars": max_chars},
        )

    @server.tool()
    def logos_register_anti_glyph(content: str, reason: str) -> str:
        return _dispatch_tool(
            session,
            "logos_register_anti_glyph",
            {"content": content, "reason": reason},
        )

    @server.tool()
    def logos_status() -> str:
        return _dispatch_tool(session, "logos_status", {})

    @server.tool()
    def logos_export_cartridge(output_path: str) -> str:
        return _dispatch_tool(session, "logos_export_cartridge", {"output_path": output_path})

    server.run()
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="logos-mcp", description="L.O.G.O.S. MCP stdio server")
    parser.add_argument(
        "--db",
        default=os.environ.get("LOGOS_DB", ":memory:"),
        help="Session SQLite DB path (default: :memory:)",
    )
    parser.add_argument("--budget", type=int, default=250_000, help="Context budget in tokens")
    parser.add_argument("--ollama", action="store_true", help="Use local Ollama embeddings")
    parser.add_argument(
        "--transport",
        choices=["auto", "jsonrpc", "fastmcp"],
        default="auto",
        help="Stdio transport (default: auto)",
    )
    args = parser.parse_args(argv)

    session = LogosSession.from_db(
        args.db,
        use_ollama=args.ollama,
        context_budget_tokens=args.budget,
    )
    try:
        if args.transport in ("auto", "fastmcp"):
            rc = serve_fastmcp_if_available(session)
            if rc is not None:
                return rc
            if args.transport == "fastmcp":
                raise RuntimeError("fastmcp transport requested but 'mcp' package is not installed")
        return serve_jsonrpc_stdio(session)
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
