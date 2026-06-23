# Chat-Outreach Engine

Pitches ecommerce brands inside their own live chat widget. See CONTEXT.md for the
glossary and docs/adr/ for decisions.

<!-- BEGIN matt-pocock-skill-chain (managed by /setup-matt-pocock-skills) -->
## Tracker contract (for grill / to-prd / to-issues / tdd / improve-codebase-architecture)

- Tracker: GitHub Issues, via the `gh` CLI, account nikhilthale22-oss.
- This project = one GitHub repo. Publish PRDs and issues here, never elsewhere.
- Triage label for AFK-ready work: `ready-for-agent`. Apply it ONLY when a PRD or
  issue is vetted AND unblocked (all its blockers are closed). The label doubles as
  the unblock gate, because ralphy grabs the first open labelled issue and does not
  read blocked-by order.
- Publish a PRD: gh issue create --label ready-for-agent --title "PRD: <name>" --body-file <file>
- Publish a slice: gh issue create --label ready-for-agent --title "<slice>" --body-file <file>
  (publish in dependency order so Blocked-by can cite real issue numbers).

## Standing rules (always honored on this project)
1. No unattended live deploy to a paying customer. On autonomous / AFK / overnight
   runs: build, test, commit, but do NOT push to a live paying customer. Hand off a
   single one-command push for Nikhil to review and run.
2. No em dashes, ever. Use a normal hyphen "-" in all prose, commits, issues, PRDs,
   code comments. Em dashes are an AI tell. Strip them from any skill-generated output.
3. Heavy or sustained compute runs on Hetzner Server #1 (chatbot-worker-01), not the
   Mac. New work in /root/<project>/; the /opt scrapers are sacred; check load first.
4. Visible testing only. Validation means real code run against real data with the raw
   output shown. Synthetic, self-constructed tests are not validation.
<!-- END matt-pocock-skill-chain -->
