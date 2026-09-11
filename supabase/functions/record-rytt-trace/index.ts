import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";
import { createRemoteJWKSet, jwtVerify } from "npm:jose@5";

const allowedOrigins = new Set([
  "https://rytt-sovereign-semiotics.vercel.app",
  "https://rytt-sovereign-semiotics-chyrho.vercel.app",
  "https://rytt-sovereign-semiotics-git-main-chyrho.vercel.app",
]);
const githubJwks = createRemoteJWKSet(
  new URL("https://token.actions.githubusercontent.com/.well-known/jwks"),
);
const githubIssuer = "https://token.actions.githubusercontent.com";
const githubAudience = "rytt-conformance";
const trustedRepository = "Mega-Therion/RYTT-Sovereign-Semiotics";
const trustedWorkflow = "Mega-Therion/RYTT-Sovereign-Semiotics/.github/workflows/rytt-core-ci.yml@refs/heads/main";

const corsHeaders = (origin: string | null): Record<string, string> => ({
  "Access-Control-Allow-Origin": origin && allowedOrigins.has(origin)
    ? origin
    : "https://rytt-sovereign-semiotics.vercel.app",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-github-oidc",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
  "Vary": "Origin",
});

const isNonNegativeInteger = (value: unknown): value is number =>
  typeof value === "number" && Number.isInteger(value) && value >= 0;

async function isTrustedGitHubRun(token: string | null): Promise<boolean> {
  if (!token) return false;
  try {
    const { payload } = await jwtVerify(token, githubJwks, {
      issuer: githubIssuer,
      audience: githubAudience,
    });
    return payload.repository === trustedRepository &&
      payload.ref === "refs/heads/main" &&
      payload.workflow_ref === trustedWorkflow;
  } catch (error) {
    console.error("GitHub OIDC validation failed", error);
    return false;
  }
}

Deno.serve(async (request: Request) => {
  const origin = request.headers.get("origin");
  const headers = corsHeaders(origin);

  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "method_not_allowed" }), {
      status: 405,
      headers,
    });
  }

  let payload: Record<string, unknown>;
  try {
    payload = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "invalid_json" }), {
      status: 400,
      headers,
    });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL") ?? "",
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
  );

  if (payload.kind === "conformance") {
    if (!await isTrustedGitHubRun(request.headers.get("x-github-oidc"))) {
      return new Response(JSON.stringify({ error: "untrusted_ci_identity" }), {
        status: 401,
        headers,
      });
    }
    const runs = payload.runs;
    const validRuns = Array.isArray(runs) && runs.length > 0 && runs.length <= 32 &&
      runs.every((run) => run && typeof run === "object" &&
        typeof run.vector_id === "string" && run.vector_id.length <= 128 &&
        typeof run.spec_version === "string" && run.spec_version.length <= 32 &&
        run.status === "passed" && run.discrepancy === 0);
    if (!validRuns) {
      return new Response(JSON.stringify({ error: "invalid_conformance_payload" }), {
        status: 400,
        headers,
      });
    }
    const { error } = await supabase.from("rytt_conformance_runs").insert(runs);
    if (error) {
      console.error("conformance insert failed", error.message);
      return new Response(JSON.stringify({ error: "conformance_write_failed" }), {
        status: 500,
        headers,
      });
    }
    return new Response(JSON.stringify({ accepted: true, rows: runs.length }), {
      status: 202,
      headers,
    });
  }

  if (origin && !allowedOrigins.has(origin)) {
    return new Response(JSON.stringify({ error: "origin_not_allowed" }), {
      status: 403,
      headers,
    });
  }

  const { session_id, input_text_length, pua_stream_length, token_count, runtime_ms, is_exact_recovery } = payload;
  const validTrace =
    typeof session_id === "string" && session_id.length >= 8 && session_id.length <= 128 &&
    isNonNegativeInteger(input_text_length) && input_text_length <= 1_000_000 &&
    isNonNegativeInteger(pua_stream_length) && pua_stream_length <= 1_000_000 &&
    isNonNegativeInteger(token_count) && token_count <= 1_000_000 &&
    typeof runtime_ms === "number" && Number.isFinite(runtime_ms) && runtime_ms >= 0 && runtime_ms <= 60_000 &&
    typeof is_exact_recovery === "boolean";

  if (!validTrace) {
    return new Response(JSON.stringify({ error: "invalid_trace_payload" }), {
      status: 400,
      headers,
    });
  }

  const { error } = await supabase.from("rytt_traces").insert({
    session_id,
    input_text_length,
    pua_stream_length,
    token_count,
    runtime_ms,
    is_exact_recovery,
    discrepancy: 0,
    spec_version: "0.1.0",
  });
  if (error) {
    console.error("rytt trace insert failed", error.message);
    return new Response(JSON.stringify({ error: "trace_write_failed" }), {
      status: 500,
      headers,
    });
  }

  return new Response(JSON.stringify({ accepted: true }), { status: 202, headers });
});
