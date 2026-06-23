# Research: current-code audit (harvested 2026-06-22)

The existing work is 4 disconnected piles. This repo absorbs the reusable parts via Build
issues; the old piles get retired (NOT kept as a 5th pile).

## The piles
- `tools/chatbot-breaker/` - the injector + chat QA. Works partially. 13 scripts have DEAD
  hardcoded iCloud paths; same 3 functions copy-pasted into 6 audit files; NO reply
  capture, NO ledger. git: 1 throwaway commit. No tests.
- `tools/chatdetect/` - the 62-vendor detector. Works (dev fork; production = `chatbot-
  outreach` on Server #1). git: 1 commit. No tests.
- `outreach/` - cold-email lists/campaigns. REJECTED channel (ADR-0001). Not absorbed.
- `conversion-engine/` - Klaviyo flow builder. Different offer. Not part of this project.

## Deployable units -> where current code maps
| Unit | Current code | State |
|---|---|---|
| source brands | outreach/lists, storeleads | data only |
| detect chat vendor | chatdetect/signatures.py | REUSE (core asset) |
| classify has-AI | chatbot-breaker/filter_ai_agent.py | reuse |
| inject pitch (per-vendor) | chatbot-breaker/send_no_ai.py | reuse Gorgias; build rest |
| capture replies | none | MISSING |
| ledger | results/pitched_brands.json (flat) | thin; needs real ledger |

## Reusable vs throwaway
- KEEP: signatures.py (62-vendor detection), send_no_ai.py (Gorgias adapter pattern),
  gorgias_config.py, strict_classifier.py, filter_ai_agent.py.
- THROWAWAY: the 6 legacy audit_*/run_* variants, outreach cold-email scripts,
  conversion-engine.

## Top anti-patterns to fix in Build
1. Dead hardcoded absolute paths (13 files).
2. Same Playwright helpers duplicated across 6 files (no shared lib).
3. No reply capture (channel success is unmeasured).
4. No real ledger (can't compare vendor/pitch reply rates).
5. Code scattered across unrelated dirs, no single repo or spine.
