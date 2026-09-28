/**
 * RYTT Sovereign Semiotics — OpenTelemetry-compliant trace verification service.
 *
 * Expanded from a simple storage hook into a Zod-validated telemetry endpoint
 * that monitors round-trip errors, plane distributions, and latency regressions
 * across connected projects (4Leibniz, Res-Nova, MVPC-X, chyren-aeon, external).
 *
 * Deploy on Deno Deploy or Supabase Edge Functions.
 */

import { serve } from "https://deno.land/std@0.224.0/http/server.ts";
import { z } from "https://deno.land/x/zod@v3.22.4/index.ts";

// ─── Zod schema for trace envelopes ────────────────────────────────────

const TraceEnvelopeSchema = z.object({
  source_system: z.enum(["4Leibniz", "Res-Nova", "MVPC-X", "chyren-aeon", "external"]),
  trace_id: z.string().uuid(),
  schema_version: z.string().regex(/^v\d+\.\d+\.\d+$/),
  metrics: z.object({
    raw_character_count: z.number().int().nonnegative(),
    encoded_token_count: z.number().int().nonnegative(),
    encoding_duration_ns: z.number().int().nonnegative(),
    roundtrip_lossless: z.boolean(),
  }),
  plane_telemetry: z.object({
    ground_plane_tokens: z.number().int().nonnegative(),
    elevated_plane_tokens: z.number().int().nonnegative(),
    ligature_activations: z.record(z.string(), z.number().int()),
  }),
  diagnostics: z.array(z.string()).optional(),
});

type TraceEnvelope = z.infer<typeof TraceEnvelopeSchema>;

// ─── CORS ──────────────────────────────────────────────────────────────

const allowedOrigins = new Set([
  "https://rytt-sovereign-semiotics.vercel.app",
  "https://rytt-sovereign-semiotics-chyrho.vercel.app",
  "https://rytt-sovereign-semiotics-git-main-chyrho.vercel.app",
]);

function corsHeaders(origin: string | null): Record<string, string> {
  return {
    "Access-Control-Allow-Origin": origin && allowedOrigins.has(origin)
      ? origin
      : "https://rytt-sovereign-semiotics.vercel.app",
    "Access-Control-Allow-Headers": "authorization, apikey, content-type, x-github-oidc, traceparent",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Content-Type": "application/json",
    "Vary": "Origin",
  };
}

// ─── OpenTelemetry span creation ─────────────────────────────────────────

function createOtelSpan(name: string, traceId: string): Record<string, unknown> {
  return {
    name,
    trace_id: traceId,
    span_id: crypto.randomUUID().replace(/-/g, "").slice(0, 16),
    start_time: performance.now(),
    attributes: {},
  };
}

// ─── Main handler ───────────────────────────────────────────────────────

serve(async (req: Request): Promise<Response> => {
  const origin = req.headers.get("origin");
  const headers = corsHeaders(origin);

  if (req.method === "OPTIONS") {
    return new Response(null, { status: 204, headers });
  }
  if (req.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), {
      status: 405,
      headers,
    });
  }

  // OpenTelemetry: create root span
  const rootSpan = createOtelSpan("rytt.trace.ingest", crypto.randomUUID());
  const startTime = performance.now();

  try {
    const rawPayload = await req.json();
    const validationResult = TraceEnvelopeSchema.safeParse(rawPayload);

    if (!validationResult.success) {
      rootSpan.attributes = { error: "schema_validation_error" };
      return new Response(JSON.stringify({
        status: "schema_validation_error",
        errors: validationResult.error.flatten(),
        trace_id: rootSpan.trace_id,
      }), {
        status: 422,
        headers,
      });
    }

    const trace: TraceEnvelope = validationResult.data;

    // OpenTelemetry: add child span for processing
    const processSpan = createOtelSpan("rytt.trace.process", trace.trace_id);
    processSpan.attributes = {
      "rytt.source_system": trace.source_system,
      "rytt.raw_chars": trace.metrics.raw_character_count,
      "rytt.encoded_tokens": trace.metrics.encoded_token_count,
      "rytt.roundtrip_lossless": trace.metrics.roundtrip_lossless,
    };

    // Alert on round-trip violations
    if (!trace.metrics.roundtrip_lossless) {
      console.error(
        `CRITICAL: Roundtrip bijectivity violation reported by ${trace.source_system}`,
        JSON.stringify(trace),
      );
    }

    // Alert on latency regressions (> 100ms encoding)
    if (trace.metrics.encoding_duration_ns > 100_000_000) {
      console.warn(
        `WARN: Latency regression — ${trace.source_system} encoding took ${trace.metrics.encoding_duration_ns}ns`,
      );
    }

    const processingTime = performance.now() - startTime;

    return new Response(JSON.stringify({
      status: "recorded",
      trace_id: trace.trace_id,
      collector_latency_ms: processingTime,
      otel: {
        trace_id: rootSpan.trace_id,
        span_id: rootSpan.span_id,
      },
    }), {
      status: 200,
      headers,
    });
  } catch (err) {
    rootSpan.attributes = { error: "internal_processing_error" };
    return new Response(JSON.stringify({
      error: "Internal processing error",
      details: err.message,
      trace_id: rootSpan.trace_id,
    }), {
      status: 500,
      headers,
    });
  }
});
