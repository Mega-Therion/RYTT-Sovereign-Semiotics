# RYTT Operations and Hardening

## Security

The public site is static and does not require authentication, cookies, or a server-side database. The Vercel configuration sets content-type sniffing, referrer, and permissions policies. The browser playground compiles locally and does not send source text to a remote service. The artifact exporter makes source inclusion explicit.

All user-controlled text rendered into HTML should use text nodes or escaped output. Portable envelopes must be verified against the local vocabulary hash before they are treated as canonical. ZIP bundles should be opened with bounded extraction in any future server-side service.

## Accessibility

Public routes use explicit language metadata, titles, main landmarks, skip links, named controls, focus-visible styles, live regions, keyboard-native controls, and reduced-motion handling. The dependency-free static audit is run with `python scripts/audit_static_site.py`. Manual browser checks should still cover keyboard traversal, 200% zoom, high contrast, and screen-reader announcements.

## Performance

`python scripts/perf_smoke.py` verifies that a long representative input compiles and round-trips. This is a smoke test, not a cross-system performance claim. Browser pages should remain static, avoid blocking third-party scripts, and keep generated vocabulary data deterministic.

## Release checklist

Run the complete test suite, canonical and conformance generators in check mode, formal-boundary alignment, artifact export/replay, benchmark arena, static audit, performance smoke, package build, and route smoke tests. Record the package version, specification version, vocabulary hash, Git commit, and Vercel deployment URL.
