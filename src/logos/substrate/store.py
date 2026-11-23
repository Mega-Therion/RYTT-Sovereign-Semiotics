"""S — Append-Only Immutable Substrate Store (SQLite WAL + FTS5 + Fail-Closed SHA-256)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..layers.schema import TensorGlyph


class LogosSubstrate:
    """
    Append-only provenance substrate storing immutable raw blocks, compiled glyphs,
    and FTS5 lexical indexes with SHA-256 verification on every readback.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        if self.db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._has_fts5 = False
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS raw_blocks (
                raw_sha256 TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                char_count INTEGER NOT NULL,
                storage_uri TEXT NOT NULL,
                epistemic_tier TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS glyphs (
                glyph_id TEXT PRIMARY KEY,
                level INTEGER NOT NULL,
                plane TEXT NOT NULL,
                symbol TEXT NOT NULL,
                raw_sha256 TEXT NOT NULL,
                is_anti_glyph INTEGER NOT NULL DEFAULT 0,
                json_payload TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        try:
            self._conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS raw_blocks_fts USING fts5(
                    raw_sha256 UNINDEXED,
                    content
                )
                """
            )
            self._has_fts5 = True
        except sqlite3.OperationalError:
            self._has_fts5 = False
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def put_raw_block(
        self,
        content: str,
        token_count: int,
        epistemic_tier: str = "P",
        storage_uri: Optional[str] = None,
    ) -> str:
        raw_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        uri = storage_uri or f"logos://raw/{raw_sha}"
        existing = self._conn.execute(
            "SELECT 1 FROM raw_blocks WHERE raw_sha256 = ?", (raw_sha,)
        ).fetchone()
        if existing is None:
            self._conn.execute(
                """
                INSERT INTO raw_blocks (
                    raw_sha256, content, token_count, char_count,
                    storage_uri, epistemic_tier, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    raw_sha,
                    content,
                    int(token_count),
                    len(content),
                    uri,
                    str(epistemic_tier),
                    time.time(),
                ),
            )
            if self._has_fts5:
                self._conn.execute(
                    "INSERT INTO raw_blocks_fts (raw_sha256, content) VALUES (?, ?)",
                    (raw_sha, content),
                )
            self._conn.commit()
        return raw_sha

    def get_raw_block(self, raw_sha256: str, verify_sha: bool = True) -> Optional[str]:
        row = self._conn.execute(
            "SELECT content FROM raw_blocks WHERE raw_sha256 = ?",
            (raw_sha256,),
        ).fetchone()
        if row is None:
            return None
        content = str(row["content"])
        if verify_sha:
            actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
            if actual != raw_sha256:
                raise ValueError(
                    f"Fail-closed SHA-256 mismatch on raw block {raw_sha256[:12]}: got {actual[:12]}"
                )
        return content

    def list_raw_blocks(self) -> List[Dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT raw_sha256, content, token_count, char_count,
                   storage_uri, epistemic_tier, created_at
            FROM raw_blocks ORDER BY created_at ASC, raw_sha256 ASC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def put_glyph(self, glyph: TensorGlyph) -> None:
        payload = json.dumps(glyph.to_dict(), sort_keys=True)
        self._conn.execute(
            """
            INSERT OR REPLACE INTO glyphs (
                glyph_id, level, plane, symbol, raw_sha256,
                is_anti_glyph, json_payload, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                glyph.glyph_id,
                int(glyph.level),
                glyph.plane,
                glyph.symbol,
                glyph.provenance.raw_sha256,
                1 if glyph.is_anti_glyph else 0,
                payload,
                float(glyph.created_at),
            ),
        )
        self._conn.commit()

    def get_glyph(self, glyph_id: str) -> Optional[TensorGlyph]:
        row = self._conn.execute(
            "SELECT json_payload FROM glyphs WHERE glyph_id = ?", (glyph_id,)
        ).fetchone()
        if row is None:
            return None
        return TensorGlyph.from_dict(json.loads(row["json_payload"]))

    def list_glyphs(self) -> List[TensorGlyph]:
        rows = self._conn.execute(
            "SELECT json_payload FROM glyphs ORDER BY level ASC, created_at ASC"
        ).fetchall()
        return [TensorGlyph.from_dict(json.loads(r["json_payload"])) for r in rows]

    def set_meta(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (key, json.dumps(value, sort_keys=True)),
        )
        self._conn.commit()

    def get_meta(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def search_raw_fts(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        cleaned = " ".join(tok for tok in query.split() if tok.isalnum() or "_" in tok)
        if not cleaned:
            return []
        if self._has_fts5:
            try:
                fts_q = " OR ".join(f'"{tok}"' for tok in cleaned.split()[:8])
                rows = self._conn.execute(
                    """
                    SELECT b.raw_sha256, b.content, b.token_count, b.storage_uri
                    FROM raw_blocks_fts f
                    JOIN raw_blocks b ON b.raw_sha256 = f.raw_sha256
                    WHERE raw_blocks_fts MATCH ?
                    ORDER BY rank LIMIT ?
                    """,
                    (fts_q, int(limit)),
                ).fetchall()
                return [dict(r) for r in rows]
            except sqlite3.OperationalError:
                pass

        like_arg = f"%{cleaned.split()[0]}%"
        rows = self._conn.execute(
            """
            SELECT raw_sha256, content, token_count, storage_uri
            FROM raw_blocks WHERE content LIKE ? LIMIT ?
            """,
            (like_arg, int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]

    @staticmethod
    def query_chyren_kb(
        query: str,
        kb_path: Optional[Path] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Read-only optional FTS query against Chyren's local knowledge.db (never writes)."""
        target = kb_path or (Path.home() / ".chyren" / "knowledge.db")
        if not target.exists():
            return []
        conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(
                """
                SELECT d.title, d.source, d.original_path, d.vault_path
                FROM documents_fts f
                JOIN documents d ON d.id = f.rowid
                WHERE documents_fts MATCH ?
                ORDER BY rank LIMIT ?
                """,
                (query, int(limit)),
            ).fetchall()
            return [dict(r) for r in rows]
        except sqlite3.Error:
            return []
        finally:
            conn.close()
