# Native worker architecture and verification

## Data flow

Desktop/Telegram parent -> installed dispatch skill -> workers.py -> existing
local Hermes gateway session.create -> native Hermes CLI attached in a named
Herdr workspace. The worker uses the configured native delegation route
(currently MiniMax-M3 / minimax-oauth) and normal default-profile local Honcho.

Conversation messages remain in Hermes' canonical store. Desktop's existing
session-list/history/resume APIs operate on those same session IDs. Herdr owns
terminals, not a competing conversation database. No ownership fields are
fabricated and no direct writes are made to Hermes SQLite.

## Private local state

`runtime/` is mode0700, ignored by Git. Prompt files and workers.json are0600.
The manifest maps worker name -> exact native session ID, title, owned pane and
workspace IDs, cwd, configured model/provider, request ID and admission status.
Atomic replacements and a file lock protect it. Gateway creation identity is
flushed before the request; native ID is flushed before prompt admission.
Recorded names are idempotent, and ambiguous starts are never auto-replayed.

No structural changes to Hermes or Honcho database schemas were made; this
integration uses their supported native APIs. There are no migrations/backfills.

## Completion and control

`wait` checks native running/pending/approval state, the exact admitted task and
its final assistant turn. It does not trust Herdr badges and does not approve
artifact quality. Parent uses terminal background completion notifications and
verifies real files/tests afterward. A timeout leaves work durable, not deleted.

`stop` verifies a native run is stopped/no pending work before closing the owned
terminal. `resume` attaches a new pane to the same native conversation ID without
creation overrides or replaying a task. No other panes or profiles are modified.

## Actual checks executed on November 6, 2026

- `python3 -m unittest test_workers -v`: **15 tests, OK**.
- `python3 install.py`: publisher digest verified, user-local links installed.
- `herdr-workers --help`: registered start/list/show/read/stop/resume/wait.
- Two real native MiniMax-M3 workers started in separate Herdr workspaces.
- memory-live called honcho_conclude to save a true user preference, then queried
  it back. recall-live independently retrieved the same conclusion in another
  native session. Both actual tool responses were checked in native history.
- Authenticated Desktop /api/profiles/sessions returned both worker rows; exact
  /api/sessions/{id}/messages returned their conversations. Native HTTP tickets
  were purpose-scoped, ephemeral, and never printed/persisted.
- `verify_desktop.py --api-base http://127.0.0.1:34185 memory-live recall-live`
  asserted listing, conversation reads and actual Honcho tool readback for both.
- memory-live was stopped and resumed: same native ID/history, new owned pane.
- `wait ... --timeout 10` returned turn_settled with the real final marker for
  each. Both test workers then stopped; Desktop history checks still passed.
- Native redacted export of memory-live parsed successfully (one session record).
- Default config.yaml and .env were byte-identical to their pre-trial hashes.
- Old safe-mode/source=tool smoke worker retired. No test agents left running.

## Failed attempts that informed the implementation

- Classic CLI --continue/--create-if-missing plus explicit route overrides created
  an empty default-route row then refused differing resume flags. No prompt was
  submitted in that attempt. Use supported gateway session.create, then attach.
- First direct RPC used a CSV toolset string and was refused invalid_params.
  Gateway requires an array; regression assertion added. No inference ran there.
- Interactive-purpose native ticket does not authenticate HTTP. Use native-http
  purpose, a fresh ticket per read, and explicit default-profile selectors.
- Large sidebar request timed out once; scoped existing session list and exact
  history routes succeeded. Do not treat a backend payload as visual UI proof.

## Existing limits deliberately preserved

Local Honcho host is http://127.0.0.1:33179, workspacehermes. Conclusion save/query
works. Independently read-only ledger inspection showed halt=malformed and gate
health inference=not_assessed. Automatic extraction/dialectic remains degraded;
no halt clearing, grant renewal, model/provider change or budget increase made.
Message-embedding/card/summary settings were not changed. No cloud-memory fallback.

The installed official Herdr identity plugin remains disposable-only. No Hermes
gateway restart or plugin activation is required. Default-profile dispatch only;
no fleet/dellmini/other-profile mutation. Native APIs use Hermes' own authentication;
no custom provider endpoints or OAuth credential copying.

Windows Desktop visual click-through was not performed (no local CDP target).
Backend visibility/history and native resume are proven separately. Herdr
working-state heuristics remain advisory. Automatic server-restart agent recovery
is disabled. Existing built-in ephemeral delegate_task and Kanban behavior are
not transparently intercepted.
