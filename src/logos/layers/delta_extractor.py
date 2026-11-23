"""Horizon 1 Hardening: Natural-Language & Live Ollama Layer-2 State Delta Extractor."""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .schema import EpistemicTier, RelationEdge, RelationType

# Legacy explicit key=value / key: value extractors (backwards-compatible)
_SLOT_KV_RE = re.compile(
    r"(?:^|[\s;])([A-Za-z][A-Za-z0-9_.-]{1,36})\s*(?:=|:=|->)\s*([^\s;,#]{1,64})"
)
_DECISION_RE = re.compile(
    r"(?im)^\s*(?:decision|canonical|endpoint|active_[a-z0-9_]+|port|model|policy|path|version)\s*[:=]\s*([^\n]+)$"
)

_LEADING_ARTICLES_RE = re.compile(
    r"^(?:the|our|a|an|current|initial|existing|default|primary|production|staging|local|system|cluster)\s+",
    re.IGNORECASE,
)

_KEY_SYNONYMS: Dict[str, str] = {
    "gateway_port": "GATEWAY_PORT",
    "gateway": "GATEWAY_PORT",
    "canonical_port": "CANONICAL_PORT",
    "ingress_port": "GATEWAY_PORT",
    "service_port": "CANONICAL_PORT",
    "gate_script": "GATE_SCRIPT",
    "verifier_script": "GATE_SCRIPT",
    "claim_gate_script": "GATE_SCRIPT",
    "claim_gate": "GATE_SCRIPT",
    "active_db": "ACTIVE_DB",
    "active_database": "ACTIVE_DB",
    "database": "ACTIVE_DB",
    "primary_db": "ACTIVE_DB",
    "primary_database": "ACTIVE_DB",
    "kv_strategy": "KV_STRATEGY",
    "kv_cache_strategy": "KV_STRATEGY",
    "cache_strategy": "KV_STRATEGY",
    "proof_tier": "PROOF_TIER",
    "epistemic_tier": "PROOF_TIER",
    "verification_tier": "PROOF_TIER",
    "cipher_suite": "CIPHER_SUITE",
    "consensus_timeout": "CONSENSUS_TIMEOUT",
    "storage_engine": "STORAGE_ENGINE",
}

# Phrase token helper: 1 to 4 whole words (\b after each word prevents intra-word character backtracking!)
_WORD = r"[A-Za-z][A-Za-z0-9_]*\b"
_PHRASE_4W = rf"{_WORD}(?:[\s-]+{_WORD}){{0,3}}"
_PHRASE_3W = rf"{_WORD}(?:[\s-]+{_WORD}){{0,2}}"
_STOP_LOOKAHEAD = r"(?=\s+(?:after|during|while|across|for|in|on|to|and|because|before|with|under|by)\b|[.,;!\n]|$)"

# Natural-language transition patterns:
# 1. "switch/move/change/update/set/migrate/upgrade [the] X from A to B"
_FROM_TO_RE = re.compile(
    r"\b(?:switch(?:ed|ing)?|mov(?:ed|ing|e)|chang(?:ed|ing|e)|updat(?:ed|ing|e)|"
    r"set(?:ting)?|migrat(?:ed|ing|e)|upgrad(?:ed|ing|e)|shift(?:ed|ing)?|"
    r"transition(?:ed|ing)?|rebound|bump(?:ed)?)\s+"
    rf"(?P<key>{_PHRASE_4W})\s+from\s+"
    r"(?P<old>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)\s+to\s+"
    r"(?P<new>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)",
    re.IGNORECASE,
)

# 2a. "ditched/deprecated/dropped/retired/abandoned/replaced [noun] A and moved/switched/set/updated [the] X to B"
_DITCH_MOVE_RE = re.compile(
    r"\b(?:ditch(?:ed)?|deprecat(?:ed|e)|drop(?:ped)?|retir(?:ed|e)|abandon(?:ed)?|replac(?:ed|e))\s+"
    rf"(?:(?P<old_noun>{_PHRASE_3W})\s+)?"
    r"(?P<old>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)\s+"
    r"(?:and|to|then)\s+"
    r"(?:now\s+)?"
    r"(?:mov(?:ed|e)|switch(?:ed)?|updat(?:ed|e)|set|bound|pointed|routed)\s+"
    rf"(?P<key>{_PHRASE_4W})\s+to\s+"
    r"(?P<new>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)",
    re.IGNORECASE,
)

# 2b. "ditched/deprecated/dropped/retired/replaced [the X] A and [now] use/adopted B [for/as [the] X]"
_DITCH_USE_RE = re.compile(
    r"\b(?:ditch(?:ed)?|deprecat(?:ed|e)|drop(?:ped)?|retir(?:ed|e)|abandon(?:ed)?|replac(?:ed|e))\s+"
    r"(?P<old>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)\s+"
    r"(?:and|in\s+favor\s+of|with)\s+"
    r"(?:now\s+)?"
    r"(?:use(?:d|s)?|using|adopt(?:ed)?|select(?:ed)?|chose)\s+"
    r"(?P<new>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)"
    rf"(?:\s+(?:for|as)\s+(?P<post_key>{_PHRASE_4W}))?{_STOP_LOOKAHEAD}",
    re.IGNORECASE,
)

# 3. "settled on / standardized on / locked in Y for/as [the] X"
_SETTLED_ON_RE = re.compile(
    r"\b(?:settled\s+on|standardized\s+on|locked\s+in|adopted|selected)\s+"
    r"(?P<new>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)\s+"
    r"(?:for|as)\s+"
    rf"(?P<key>{_PHRASE_4W}){_STOP_LOOKAHEAD}",
    re.IGNORECASE,
)

# 4. "[the] X is now Y" / "[the] X stood at Y" / "[the] X was set to Y" / "bound/pointed/set [the] X to Y"
_IS_NOW_RE = re.compile(
    rf"\b(?P<key>{_PHRASE_3W})\s+"
    r"(?:is\s+now|now\s+equals|stood\s+at|was\s+set\s+to|remains\s+set\s+to|defaults\s+to)\s+"
    r"(?P<new>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)"
    rf"{_STOP_LOOKAHEAD}",
    re.IGNORECASE,
)

_BOUND_TO_RE = re.compile(
    r"\b(?:bound|pointed|set|configured|initialized|routed|pinned)\s+"
    rf"(?P<key>{_PHRASE_4W})\s+to\s+"
    r"(?P<new>[`'\"]?[A-Za-z0-9_./:-]+[`'\"]?)"
    rf"{_STOP_LOOKAHEAD}",
    re.IGNORECASE,
)

# 5. "rejected / disproved / falsified / ruled out <CLAIM> because / due to / since <REASON>"
_ANTI_CLAIM_RE = re.compile(
    r"\b(?P<verb>rejected|disproved|disproven|falsified|ruled\s+out|abandoned|quarantined)\s+"
    r"(?:hypothesis\s+|branch\s+|claim\s+|approach\s+)?"
    r"(?P<claim>[`'\"]?[A-Za-z0-9_./:-]{3,64}[`'\"]?)\s+"
    r"(?:because|due\s+to|since|as|after\s+finding\s+that)\s+"
    r"(?P<reason>[^.\n;]{4,160})",
    re.IGNORECASE,
)

# 6. Multi-hop relational edges in prose: "<A> depends on / verifies / refutes / is derived from <B>"
_PROSE_RELATION_RE = re.compile(
    r"\b(?P<src>[A-Za-z0-9_./:-]{3,64})\b\s+"
    r"(?:in\s+turn\s+|directly\s+)?"
    r"(?P<rel>depends\s+on|requires|verifies|validates|refutes|contradicts|is\s+derived\s+from|extends)\s+"
    r"(?:the\s+(?:artifact|module|script|digest|theorem|pointer|branch)\s+(?:at\s+|digest\s+)?)?"
    r"(?P<dst>[A-Za-z0-9_./:-]{3,64})",
    re.IGNORECASE,
)

_IGNORED_KEY_WORDS = frozenset({
    "we", "it", "this", "that", "they", "he", "she", "who", "which", "what",
    "traffic", "requests", "packets", "calls", "users", "nodes", "workers", "all",
})


def _clean_val(raw: str) -> str:
    return raw.strip().strip("`'\"").rstrip(".,;:")


def normalize_slot_key(raw_key: str, old_val: str = "", new_val: str = "", old_noun: str = "") -> str:
    """Normalize a natural-language slot phrase into a canonical UPPER_SNAKE_CASE identifier."""
    cleaned = raw_key.strip().strip("`'\".,;:")
    if not cleaned:
        cleaned = old_noun.strip()

    # If already an explicit UPPER_SNAKE_CASE or snake_case identifier without spaces, keep or uppercase
    if re.fullmatch(r"[A-Z][A-Z0-9_]{1,35}", cleaned):
        return cleaned

    # Strip leading articles/modifiers repeatedly
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = _LEADING_ARTICLES_RE.sub("", cleaned).strip()

    # Strip trailing filler words like "value" or "setting" or "parameter"
    cleaned = re.sub(r"\s+(?:value|setting|parameter|option|config|configuration|slot)$", "", cleaned, flags=re.IGNORECASE).strip()

    snake = re.sub(r"[\s-]+", "_", cleaned.lower()).strip("_")
    if old_noun:
        noun_clean = _LEADING_ARTICLES_RE.sub("", old_noun.strip()).strip().lower()
        if noun_clean == "port" and "port" not in snake:
            snake = f"{snake}_port" if snake else "gateway_port"

    if snake in _KEY_SYNONYMS:
        return _KEY_SYNONYMS[snake]

    # Heuristic inference when key is generic or missing
    sample_val = (new_val or old_val).lower()
    if snake in {"", "it", "target", "path", "file", "script"}:
        if sample_val.endswith(".py") or "gate" in sample_val:
            return "GATE_SCRIPT"
        if sample_val.endswith(".db") or sample_val.endswith(".sqlite"):
            return "ACTIVE_DB"
    if snake == "port" and (new_val.isdigit() or old_val.isdigit()):
        return "GATEWAY_PORT"

    return snake.upper() if snake else "STATE_SLOT"


def _infer_key_from_values(old_val: str, new_val: str) -> str:
    for v in (new_val, old_val):
        vl = v.lower()
        if vl.endswith(".py") or "gate" in vl:
            return "GATE_SCRIPT"
        if vl.endswith(".db") or vl.endswith(".sqlite"):
            return "ACTIVE_DB"
        if vl.isdigit() and 80 <= int(vl) <= 65535:
            return "GATEWAY_PORT"
        if vl in {"d", "p", "o", "f"}:
            return "PROOF_TIER"
        if "pages" in vl or "prefix" in vl or "kv" in vl:
            return "KV_STRATEGY"
    return "ACTIVE_TARGET"


@dataclass
class DeltaExtractionResult:
    """Structured Layer-2 output from natural-language or LLM-assisted delta extraction."""

    slots: Dict[str, str] = field(default_factory=dict)
    supersessions: Dict[str, str] = field(default_factory=dict)
    relations: List[RelationEdge] = field(default_factory=list)
    anti_claims: List[Dict[str, str]] = field(default_factory=list)
    backend: str = "deterministic-nl"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slots": dict(self.slots),
            "supersessions": dict(self.supersessions),
            "relations": [r.to_dict() for r in self.relations],
            "anti_claims": list(self.anti_claims),
            "backend": self.backend,
        }


class NaturalLanguageDeltaExtractor:
    """
    Deterministic natural-language + structured KV Layer-2 delta extractor.

    Extracts:
      - `slots`: latest active state slot assignments (`KEY -> NEW_VALUE`)
      - `supersessions`: prior values explicitly replaced inside the turn (`KEY -> OLD_VALUE`)
      - `relations`: typed `RelationEdge` items (`SUPERSEDES`, `REFUTES`, `DEPENDS_ON`, `VERIFIES`, `DERIVED_FROM`)
      - `anti_claims`: falsified/disproven hypotheses or branches (`EpistemicTier.F`)
    """

    backend_name: str = "deterministic-nl"

    def extract(self, text: str, glyph_id: str = "self") -> DeltaExtractionResult:
        slots: Dict[str, str] = {}
        supersessions: Dict[str, str] = {}
        relations: List[RelationEdge] = []
        anti_claims: List[Dict[str, str]] = []
        now = time.time()

        # 1. Explicit KEY=VALUE / KEY:=VALUE / KEY->VALUE
        for key, val in _SLOT_KV_RE.findall(text):
            k_clean = key.strip()
            v_clean = _clean_val(val)
            if k_clean.lower() in {"http", "https", "sha256", "port"}:
                if k_clean.lower() == "port" and v_clean.isdigit():
                    # Note: `port:18443` is matched by colon token, not `=`, so `port=18443` is an explicit slot
                    slots[k_clean] = v_clean
                continue
            if v_clean:
                slots[k_clean] = v_clean

        for match in _DECISION_RE.finditer(text):
            full = match.group(0)
            sep = ":" if ":" in full else "="
            raw_k, raw_v = full.split(sep, 1)
            k_clean = raw_k.strip()
            v_clean = _clean_val(raw_v)
            if k_clean and v_clean:
                slots.setdefault(k_clean, v_clean)

        # 2. Natural-language "bound / set / pointed X to Y" & "X is now Y" (run before transitions so transitions in same text can override)
        for rx in (_BOUND_TO_RE, _IS_NOW_RE, _SETTLED_ON_RE):
            for m in rx.finditer(text):
                raw_k = m.group("key").strip()
                first_tok = raw_k.split()[0].lower() if raw_k.split() else ""
                if first_tok in _IGNORED_KEY_WORDS or len(raw_k) < 2:
                    continue
                new_v = _clean_val(m.group("new"))
                if not new_v or new_v.lower() in _IGNORED_KEY_WORDS:
                    continue
                norm_k = normalize_slot_key(raw_k, new_val=new_v)
                if norm_k in slots and slots[norm_k] != new_v:
                    supersessions.setdefault(norm_k, slots[norm_k])
                slots[norm_k] = new_v

        # 3. Natural-language "switched/moved/updated/changed X from A to B"
        for m in _FROM_TO_RE.finditer(text):
            raw_k = m.group("key").strip()
            old_v = _clean_val(m.group("old"))
            new_v = _clean_val(m.group("new"))
            if not old_v or not new_v:
                continue
            norm_k = normalize_slot_key(raw_k, old_val=old_v, new_val=new_v)
            slots[norm_k] = new_v
            supersessions[norm_k] = old_v
            relations.append(
                RelationEdge(
                    source_id=glyph_id,
                    target_id=f"slot:{norm_k}:{old_v}",
                    relation=RelationType.SUPERSEDES,
                    key=norm_k,
                    note=f"{norm_k}: '{old_v}' -> '{new_v}'",
                    timestamp=now,
                )
            )

        # 4a. Natural-language "ditched [noun] A and moved [the] X to B"
        for m in _DITCH_MOVE_RE.finditer(text):
            old_noun = (m.group("old_noun") or "").strip()
            old_v = _clean_val(m.group("old"))
            raw_k = m.group("key").strip()
            new_v = _clean_val(m.group("new"))
            if not old_v or not new_v:
                continue
            norm_k = normalize_slot_key(raw_k, old_val=old_v, new_val=new_v, old_noun=old_noun)
            slots[norm_k] = new_v
            supersessions[norm_k] = old_v
            relations.append(
                RelationEdge(
                    source_id=glyph_id,
                    target_id=f"slot:{norm_k}:{old_v}",
                    relation=RelationType.SUPERSEDES,
                    key=norm_k,
                    note=f"{norm_k}: '{old_v}' -> '{new_v}'",
                    timestamp=now,
                )
            )

        # 4b. Natural-language "deprecated/ditched/dropped A and [now] use B [for X]"
        for m in _DITCH_USE_RE.finditer(text):
            old_v = _clean_val(m.group("old"))
            new_v = _clean_val(m.group("new"))
            if not old_v or not new_v or new_v.lower() in {"moved", "switched", "updated", "bound", "set", "the"}:
                continue
            raw_k = (m.group("post_key") or "").strip()
            if raw_k:
                norm_k = normalize_slot_key(raw_k, old_val=old_v, new_val=new_v)
            else:
                norm_k = _infer_key_from_values(old_v, new_v)
            slots[norm_k] = new_v
            supersessions[norm_k] = old_v
            relations.append(
                RelationEdge(
                    source_id=glyph_id,
                    target_id=f"slot:{norm_k}:{old_v}",
                    relation=RelationType.SUPERSEDES,
                    key=norm_k,
                    note=f"{norm_k}: '{old_v}' -> '{new_v}'",
                    timestamp=now,
                )
            )

        # 5. Rejected / disproved / falsified claims -> EpistemicTier.F Anti-Claims
        for m in _ANTI_CLAIM_RE.finditer(text):
            claim = _clean_val(m.group("claim"))
            reason = m.group("reason").strip().rstrip(".,;")
            if not claim or claim.lower() in _IGNORED_KEY_WORDS:
                continue
            anti_claims.append(
                {
                    "claim": claim,
                    "reason": reason,
                    "epistemic_tier": EpistemicTier.F.value,
                }
            )
            relations.append(
                RelationEdge(
                    source_id=glyph_id,
                    target_id=claim,
                    relation=RelationType.REFUTES,
                    key=claim,
                    note=reason,
                    timestamp=now,
                )
            )

        # 6. Multi-hop prose relation edges (depends on, verifies, derived from, refutes)
        for m in _PROSE_RELATION_RE.finditer(text):
            src = _clean_val(m.group("src"))
            dst = _clean_val(m.group("dst"))
            rel_raw = re.sub(r"\s+", " ", m.group("rel").lower().strip())
            if src.lower() in _IGNORED_KEY_WORDS or dst.lower() in _IGNORED_KEY_WORDS:
                continue
            if rel_raw in ("depends on", "requires"):
                rel_type = RelationType.DEPENDS_ON
            elif rel_raw in ("verifies", "validates"):
                rel_type = RelationType.VERIFIES
            elif rel_raw == "is derived from":
                rel_type = RelationType.DERIVED_FROM
            elif rel_raw == "contradicts":
                rel_type = RelationType.CONTRADICTS
            elif rel_raw == "extends":
                rel_type = RelationType.EXTENDS
            else:
                rel_type = RelationType.REFUTES
            relations.append(
                RelationEdge(
                    source_id=src,
                    target_id=dst,
                    relation=rel_type,
                    key=src,
                    note=f"{src} {rel_raw} {dst}",
                    timestamp=now,
                )
            )

        return DeltaExtractionResult(
            slots=slots,
            supersessions=supersessions,
            relations=relations,
            anti_claims=anti_claims,
            backend=self.backend_name,
        )


class OllamaStateDeltaExtractor:
    """
    LLM-assisted Layer-2 State Delta Extractor backed by local Ollama (`qwen2.5:1.5b` or `phi4-mini:latest`)
    via stdlib `urllib.request` (`/api/generate` with `format: "json"`), fused with
    `NaturalLanguageDeltaExtractor` as an always-on deterministic anchor & offline fallback.
    """

    def __init__(
        self,
        model: str = "qwen2.5:1.5b",
        base_url: str = "http://127.0.0.1:11434",
        timeout: float = 8.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = float(timeout)
        self.backend_name = f"ollama-delta:{model}"
        self.fallback = NaturalLanguageDeltaExtractor()
        self.last_fallback: bool = False
        self._cache: Dict[str, DeltaExtractionResult] = {}

    def _query_ollama_json(self, text: str) -> Dict[str, Any]:
        prompt = (
            "Extract state slot updates, supersessions, dependencies, and disproven claims from the text below.\n"
            "Return ONLY valid JSON with keys:\n"
            '  "slots": {"SLOT_NAME": "current_value"},\n'
            '  "supersessions": {"SLOT_NAME": "previous_old_value"},\n'
            '  "relations": [{"source": "A", "target": "B", "relation": "supersedes|depends_on|verifies|refutes"}],\n'
            '  "anti_claims": [{"claim": "NAME", "reason": "why rejected or disproved"}]\n'
            f"\nTEXT:\n{text}\n"
        )
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "format": "json",
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 96},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            outer = json.loads(resp.read().decode("utf-8"))
        raw_resp = outer.get("response", "{}")
        parsed = json.loads(raw_resp)
        if not isinstance(parsed, dict):
            raise ValueError("Ollama JSON response is not a JSON object")
        return parsed

    def extract(self, text: str, glyph_id: str = "self") -> DeltaExtractionResult:
        cache_key = hashlib.sha256(f"{glyph_id}:{text}".encode("utf-8")).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        base = self.fallback.extract(text, glyph_id=glyph_id)
        slots = dict(base.slots)
        supersessions = dict(base.supersessions)
        relations = list(base.relations)
        anti_claims = list(base.anti_claims)

        try:
            llm_data = self._query_ollama_json(text)
            self.last_fallback = False
            backend = self.backend_name

            raw_slots = llm_data.get("slots")
            if isinstance(raw_slots, dict):
                for k, v in raw_slots.items():
                    if isinstance(k, str) and isinstance(v, (str, int, float)) and str(v).strip():
                        val_str = _clean_val(str(v))
                        # Only accept values grounded in the text to prevent LLM hallucination
                        if val_str and val_str.lower() in text.lower():
                            norm_k = normalize_slot_key(k, new_val=val_str)
                            slots.setdefault(norm_k, val_str)

            raw_sup = llm_data.get("supersessions")
            if isinstance(raw_sup, dict):
                for k, old_v in raw_sup.items():
                    if isinstance(k, str) and isinstance(old_v, (str, int, float)) and str(old_v).strip():
                        old_str = _clean_val(str(old_v))
                        if old_str and old_str.lower() in text.lower():
                            norm_k = normalize_slot_key(k, old_val=old_str)
                            supersessions.setdefault(norm_k, old_str)

            raw_anti = llm_data.get("anti_claims")
            if isinstance(raw_anti, list):
                existing_claims = {c["claim"] for c in anti_claims}
                for item in raw_anti:
                    if isinstance(item, dict):
                        cl = _clean_val(str(item.get("claim", "")))
                        rs = str(item.get("reason", "")).strip()
                        if cl and rs and cl.lower() in text.lower() and cl not in existing_claims:
                            anti_claims.append(
                                {
                                    "claim": cl,
                                    "reason": rs,
                                    "epistemic_tier": EpistemicTier.F.value,
                                }
                            )
                            existing_claims.add(cl)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, KeyError, json.JSONDecodeError):
            self.last_fallback = True
            backend = base.backend

        result = DeltaExtractionResult(
            slots=slots,
            supersessions=supersessions,
            relations=relations,
            anti_claims=anti_claims,
            backend=backend,
        )
        self._cache[cache_key] = result
        return result
