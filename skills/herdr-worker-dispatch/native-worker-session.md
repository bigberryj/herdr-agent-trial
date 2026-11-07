# Native worker sessions: creation, visibility, memory

Depth for the `herdr-worker-dispatch` workflow. Read when a dispatch needs the
mechanics rather than the decision rules.

## Why the classic CLI path breaks

A named classic launch that passes route overrides can create the conversation
and then refuse to continue it, because the gateway freezes the creation policy
and the resume step rejects any override that differs from it. The error names
the differing flags, so the fix is not "retry with fewer flags" — it is to stop
mixing creation policy with resume.

Working shape:

- Create the session once through the authenticated local gateway
  `session.create` with an explicit title, cwd, provider/model, toolset list,
  turn cap, and `safe_mode`/`ignore_user_config`/`ignore_rules` all false.
- Attach the terminal client with `--resume <session_id>` and a query file,
  with no creation flags at all.
- Toolset names must be an **array** in the RPC contract; a comma string is
  refused as invalid parameters. Check the contract's parameter list at runtime
  and refuse to launch if a requested field is unsupported.

Consequences to carry forward:

- `source=tool` and `source=oneshot` rows exist in the session store but are
  excluded from the Desktop recents/sidebar, the stored picker and session
  recall. They are invisible, not missing.
- Distinguish workers by **title**, not by inventing a source label.
- The CLI may refuse a `--source` value the gateway does not advertise.

## Proving Desktop visibility

Backend routes, in the order that answers "can Byron see it?":

- `GET /api/profiles/sessions/sidebar` with `recents_profile=default` plus an
  explicit exclude list — this is the batched route the sidebar actually uses.
- `GET /api/profiles/sessions?profile=<profile>` for the per-profile list.
- `GET /api/sessions/{id}/messages?profile=<profile>` for the transcript.

These are authenticated. Mint a **native-http purpose** ticket per request and
send it in the gateway ticket header; an interactive-purpose ticket is not HTTP
authority. Keep tickets in memory — never print or persist them — and pass an
explicit profile selector, because omitted selectors mean "current" and can
silently read another profile.

A row in the session store, a terminal export, or a parent summary is not
proof of Desktop visibility. Conversely, a successful backend read is not a
visual click-through — say which one you performed.

## Identity: unify the human peer before sharing memory

A worker's conclusion is only visible to Byron's chat if both resolve to the
**same human peer**. Two things decide it:

- The runtime identity the transport supplies (a Unix uid for local/CLI
  sessions, a messaging-platform id for gateway chats).
- The configured peer name plus any alias map.

Resolution order: pinned peer name, then an alias of the runtime identity, then
a prefixed runtime identity, then the raw runtime identity, then the peer name
as a last resort. So without an alias, CLI and messaging sessions become two
different observed peers — the memory store is shared, the peer is not.

Fixing it:

1. Back up the memory config file (0600) before editing.
2. In the default memory host block, map each runtime identity to the intended
   human peer (`userPeerAliases`), keeping any pre-existing aliases.
3. Apply the same aliasing to every other local host block that uses the same
   human peer, so per-profile AI peers stay separate while the human peer is
   shared.
4. Leave host blocks with no local endpoint untouched, and never point a block
   at a hosted endpoint to "make it work".
5. Prove the mapping with a resolution probe that instantiates the memory
   manager per runtime identity and prints the resolved peer — do not infer it
   from the config text.
6. Verify with a real write then an exact-ID read on the loopback endpoint, and
   confirm the conclusion's observed peer is the unified one.
7. If an earlier run wrote the same fact under the old peer, delete that
   duplicate through the supported conclusion-delete API — never by editing the
   database.

## A query that returns nothing is not proof of absence

Conclusion list/search filters can miss a record that is present: a
peer-scoped literal query string may return an empty list while the unfiltered
peer list returns the record, and semantic search may return only excerpts
from a previous session rather than the conclusion itself. Treat an empty
filtered result as inconclusive and fall back to an unfiltered peer list plus a
content match, and an exact-ID GET for the final proof.

## Stopping and resuming

- Closing a pane removes a terminal; it does not cancel a gateway-owned model
  run. Interrupt the native session, then poll until running is false and
  nothing is pending, and only then close the pane.
- Resume attaches the same native session ID in a new owned pane, with no
  creation overrides and no prompt replay.
- Keep the mapping (worker name, native session ID, pane/workspace IDs) in a
  private manifest, and make a repeated launch request idempotent so a
  duplicate prompt can never be admitted.
