import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "npm:@supabase/supabase-js@2";

const allowedOrigins = new Set([
  "https://rytt-sovereign-semiotics.vercel.app",
  "https://rytt-sovereign-semiotics-chyrho.vercel.app",
  "https://rytt-sovereign-semiotics-git-main-chyrho.vercel.app",
]);

const corsHeaders = (origin: string | null): Record<string, string> => ({
  "Access-Control-Allow-Origin": origin && allowedOrigins.has(origin)
    ? origin
    : "https://rytt-sovereign-semiotics.vercel.app",
  "Access-Control-Allow-Headers": "authorization, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Content-Type": "application/json",
  "Vary": "Origin",
});

const isNonNegativeInteger = (value: unknown): value is number =>
  typeof value === "number" && Number.isInteger(value) && value >= 0;

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
  if (origin && !allowedOrigins.has(origin)) {
    return new Response(JSON.stringify({ error: "origin_not_allowed" }), {
      status: 403,
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

  const { session_id, input_text_length, pua_stream_length, token_count, runtime_ms, is_exact_recovery } = payload;
  const valid =
    typeof session_id === "string" && session_id.length >= 8 && session_id.length <= 128 &&
    isNonNegativeInteger(input_text_length) && input_text_length <= 1_000_000 &&
    isNonNegativeInteger(pua_stream_length) && pua_stream_length <= 1_000_000 &&
    isNonNegativeInteger(token_count) && token_count <= 1_000_000 &&
    typeof runtime_ms === "number" && Number.isFinite(runtime_ms) && runtime_ms >= 0 && runtime_ms <= 60_000 &&
    typeof is_exact_recovery === "boolean";

  if (!valid) {
    return new Response(JSON.stringify({ error: "invalid_trace_payload" }), {
      status: 400,
      headers,
    });
  }

  const supabase = createClient(
    Deno.env.get("SUPABASE_URL") ?? "",
    Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "",
  );
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
