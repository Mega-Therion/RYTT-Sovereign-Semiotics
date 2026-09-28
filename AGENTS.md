# AGENTS.md — Base44 dev environment notes

See `CLAUDE.md` for project/proof guidance.

## Running in Base44
- The web app is a **plain static site** (no build step): `index.html`, `styles.css`, `web/`, `renderers/`, `assets/`, deployed to Vercel (`vercel.json`).
- `docker-compose.base44.yml` serves the repo root read-only with `python -m http.server` on port 3000. Edits show on browser refresh (no HMR).
- Vercel `cleanUrls` is not emulated; internal links use explicit `.html` paths, so this is fine.
- No secrets needed. `web/playground.html` posts optional telemetry to a hosted Supabase edge function using a hardcoded publishable key; its CORS allowlist only covers the Vercel origins, so those calls fail harmlessly from the preview.
- `supabase/functions/` (Deno edge function) and the Rust crate / Lean proofs are not part of the served site and are not run here.

## Verify
- `curl -s localhost:3000/ | grep RYTT`, plus `/web/playground.html`, `/web/codex.html`, `/web/wasm/rytt_core_bg.wasm` (served as `application/wasm`).
- Python tests: `pytest tests/` (not wired into compose).
