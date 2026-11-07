# Herdr worker integration — implemented and live-verified

## Verified update — November 6, 2026

The native-session dispatch path is implemented and the default-profile skill
`herdr-worker-dispatch` is installed. It guides persistent project workers from
Desktop/Telegram into Herdr without replacing the built-in ephemeral delegation
function. No gateway restart or production identity-plugin install was needed.

Real MiniMax-M3 workers `memory-live` and `recall-live` were created via the
supported authenticated local gateway session.create API (source=cli, normal
config, explicit configured delegation route, bounded turns), then attached in
Herdr with the native CLI by session ID. This avoids an observed classic CLI
named-create/override mismatch. RPC toolsets must be an array.

- First worker saved a true standing user preference using honcho_conclude and
  queried it back. Second worker independently queried that same saved record.
- Native transcript tool results confirmed both operations, not just agent prose.
- Authenticated Desktop /api/profiles/sessions, the actual batched sidebar route,
  and exact /api/sessions/{id}/messages returned both worker conversations.
  A direct authenticated GET of the saved conclusion on the loopback Honcho
  endpoint returned200 and the exact preference (not just a tool's assertion).
  Native HTTP tickets were purpose-scoped grants kept in memory, never printed
  or persisted; no OAuth tokens copied.
- Worker stop verified native running=false/no pending work before closing its
  pane. Resume reused the exact same native session ID and history.
- Native wait returned turn_settled with actual final responses for both workers;
  no Herdr status badge used as task-completion proof. Parent still verifies work.
- 15 offline unit tests cover dispatch bounds, local-memory guard, idempotency,
  durable request IDs, native flags, RPC array shape and settlement exclusions.

## Memory limitation — resolved 2026-11-07

The local Honcho inference gate is **repaired**. Its halt was a local
misclassification, not an upstream quota problem: MiniMax-M3 legitimately
returns `stop_reason: max_tokens` when a response hits the output cap, the
gate treated that as a malformed provider response, and because every
non-ok completion latches the halt, one truncated extraction closed the gate
for ten days (2026-10-28 → 2026-11-07). 619 representation work units failed
with 403 and all memory writes stopped.

Fix shipped as `honcho-minimax/gate_serve.py` + `honcho_ops/budget.py` on
branch `fix/gate-truncation-outcome` (PR
bigberryj/honcho-subscription-bridge#2). Truncation is now a charged,
request-scoped, non-latching outcome. Verified live: truncated → 502 with no
halt, next request → 200, 22 real inferences succeeded, byron's peer
representation regenerated and its documents were updated.

Consequence for this repo: **local Honcho inference works again.** Worker
conclusions, peer cards and representations all land in the shared local
store under the unified `byron` peer, so workers and normal sessions recall
each other's memory. The watchdog that failed to self-heal was re-armed with a
1008-run budget. The 619 historical failed work units remain
processed-with-error — requeueing them costs ~131 requests / ~1.07M reserved
tokens against 61 requests / 132,976 tokens remaining, so that is an
explicit operator decision, not a background task.

**Older progress notes below are historical and superseded by this update.**


## Operator request

From Desktop/Telegram, launch project agents into Herdr without manual terminal
management. Keep native sessions/conversations visible and resumable in Desktop.
Use existing LOCAL Honcho with workers as well as parent chats. Do not move
memory to cloud, copy OAuth tokens, change memory inference grants/budgets,
replace other profiles or rewrite the Hermes core delegation function.

## Implemented locally, NOT live-verified or activated yet

- Branch feat/hermes-workers, based on pinned trial commit8d368c1.
- workers.py: scoped native Hermes CLI launcher, named Herdr workspaces, private
  prompt files/manifest, max2 managed workers, per-worker max1..40 turns.
- Uses configured delegation provider/model through native Hermes authentication.
- Real source=cli, normal user config (NOT safe-mode/ignore-rules/source=tool),
  named native conversations and no custom conversation database.
- Read action uses supported native redacted session export; exact title lookup
  is read-only SQLite, no data or ownership edits.
- Repeated names are idempotent; ambiguous start returns inspect_required rather
  than resubmitting; untracked live names/prior prompt files are refused.
- Dedicated Herdr server can be started if absent; incompatible servers are not
  replaced. No Hermes gateway start/stop/restart operation.
- **8 offline tests passed** via python3 -m unittest test_workers -v.

## Pending acceptance gates

Two read-only agents are checking exact Desktop ownership/history filtering and
local Honcho effective configuration. Parent must verify their findings before
launching a normal-memory worker. No live worker has been launched by workers.py.

Then exercise a synthetic worker request from parent, confirm native session ID,
Desktop list/detail/history access through actual authenticated client/backend,
local Honcho ingest AND recall under existing authorization, and stop/resume.
Do not call a SQLite row or localhost health endpoint end-to-end proof.

Publish a reusable dispatch skill only after those gates pass, so future Desktop
and Telegram sessions use the launcher for independent persistent workers by
default. Do not claim built-in delegate_task is transparently intercepted.
Keep short ephemeral helpers and existing durable queue semantics explicit.

Parent owns edits/security/activation/verification/feature push. Findings or
stubs are not completion. Runtime/private prompts/manifests stay ignored.
