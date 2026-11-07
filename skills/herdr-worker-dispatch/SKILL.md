---
name: herdr-worker-dispatch
description: "Use when dispatching persistent project agents."
version: 1.1.0
author: J5
license: MIT
metadata:
  hermes:
    tags: [herdr, delegation, desktop, telegram, honcho]
---

# Persistent project workers: Herdr + native Hermes + shared local memory

## When to Use

- Byron asks for independent project, coding or research workers from Desktop,
  Telegram or terminal, and expects them watchable in Herdr, reopenable in
  Desktop later, and sharing the existing local Honcho memory.
- Do NOT use for single tool calls, quick lookups, or Kanban/fleet cards; those
  keep their own semantics.
- This is skill-guided dispatch. Never claim the built-in ephemeral delegation
  path was transparently intercepted, and never present a hidden helper
  transcript as a visible Herdr worker.

## Standing rules

1. **Dispatch, don't hand-manage.** Use the `herdr-workers` CLI
   (`~/.local/bin/herdr-workers`); never reconstruct the session-creation flags
   by hand — the CLI path has known policy traps.
2. **Native sessions only.** A worker must be a real gateway session created
   with `source=cli`. A hidden source (`tool`, `oneshot`) is invisible to the
   Desktop sidebar and to session recall. Safe-mode / ignore-config launches
   disable plugins and therefore memory — never use them for real workers.
3. **History is the native session ID.** Return the session ID and the
   `[Herdr] <name> <id>` title. Prove Desktop visibility through the
   Desktop's own authenticated routes, never through a SQLite row.
4. **Local memory only, fail closed.** Require the enabled local Honcho
   provider/plugin and a reachable loopback endpoint before launching. No cloud
   fallback, no credential copying, no grant/capture/budget changes, no
   halt clearing.
5. **Unify the human peer first.** If a runtime identity (for example a
   Unix-uid or a messaging-platform id) is not aliased to the configured human
   peer, worker conclusions land under a *different* observed peer than
   Byron's own chat — shared storage without shared recall. See
   `references/native-worker-session.md`.
6. **Bounded concurrency and turns.** Max 2 managed workers, 1..40 turns each,
   default 20. Reuse the operator's configured delegation provider/model and
   native authentication.
7. **Ambiguity is not failure.** `inspect_required` or an ambiguous wait status
   means the prompt may already be admitted: read the native conversation
   before doing anything. Never resubmit on an ambiguous status alone.
8. **Completion is native settlement plus parent verification.** Wait on the
   admitted prompt, running/pending/approval state and final assistant turn;
   then verify real files/tests yourself. Herdr's idle/working/done badges are
   advisory and can miss working transitions entirely.
9. **Stop means stop the work.** Interrupt/verify the native run and confirm
   nothing is pending before closing the owned pane; a closed pane does not
   cancel gateway-owned inference. Resume attaches the *same* native session ID.
10. **Private state stays private.** Task files and the worker manifest are
    private (0600) runtime state; never commit them, quote transcripts, or
    persist native HTTP tickets or credentials.
11. **Explain to Byron in plain language first.** For a newly installed
    workflow, lead with the literal command and what he will see; give
    architecture, IDs and evidence after he asks. A dense architecture answer
    to "how do I use it" is a failed answer.
12. **The parent keeps authority.** Review, security, deploy, merge and
    promotion decisions stay with the parent conversation.

## Procedure

1. Inspect `herdr-workers list` — reuse an existing worker instead of
   duplicating one, and respect the 2-worker cap.
2. Scope the task: explicit project cwd, acceptance criteria, files allowed,
   explicit no-commit/no-deploy boundaries, evidence required, and the turn
   budget. Write it to a private task file (0600) under the runtime directory;
   never put prompt text or secrets in command arguments.
3. Launch:
   ```sh
   herdr-workers start --name <unique-worker> \
     --cwd <absolute-project-directory> \
     --prompt-file <private-task-file> --max-turns 20
   ```
   The launcher starts the dedicated workbench server if absent, creates the
   native session, then attaches the CLI and submits the prompt once.
4. Read the returned `session_id` and title. Report both to Byron. If
   `launch_status` is not `started`, do not retry the prompt — inspect first.
5. Before ending the turn, start a bounded completion wait with the terminal
   tool's background+notify so the real result wakes the parent:
   ```sh
   herdr-workers wait <worker> --timeout 600
   ```
   `turn_settled` / `needs_input` / `still_pending` are conversation states,
   not artifact-quality approvals. Escalate native approval/question state
   instead of auto-answering it.
6. Verify the worker's claims against real artifacts and test output, then
   report. Use `herdr-workers read <worker>` for the native conversation and
   `show` for the manifest; keep large exports out of the parent context.
7. `stop` and `resume` only for workers the launcher owns.

## Known limits

- The local memory inference gate was repaired on 2026-11-07 (a provider
  `stop_reason: max_tokens` response had been misclassified as malformed, and
  one such response latched the halt for ten days). Local inference now works:
  real inferences land, peer representations and cards regenerate, and the
  human peer's documents are updated. Still fail closed — never clear a halt,
  mint/extend a grant, raise a cap or switch providers to make this look
  healthy; those are the operator's decisions. The 619 representation work
  units that failed during the outage stay processed-with-error; requeueing
  them is a separate, explicitly costed decision.
- Backend route proof is not a visual Desktop click-through; say which one you
  actually performed.
- Automatic agent recovery after a workbench-server reboot is not guaranteed.
- Test conversations stay in Desktop history by design; do not delete native
  sessions to tidy up.

Depth for the native-session mechanics, Desktop verification routes and peer
unification lives in `references/native-worker-session.md`.
