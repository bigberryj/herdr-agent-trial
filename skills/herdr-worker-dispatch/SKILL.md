---
name: herdr-worker-dispatch
description: "Use when dispatching persistent project agents."
version: 1.0.0
author: J5
license: MIT
metadata:
  hermes:
    tags: [herdr, delegation, desktop, telegram, honcho]
---

# Persistent project workers: Herdr + native Hermes + local Honcho

## Operator's workflow

For independent project/coding/research worker tasks requested from Desktop,
Telegram or terminal, use this dispatcher by default so Byron can watch their
terminals in Herdr and reopen native conversations in Desktop later. Byron need
not explicitly say Herdr each time. Keep parent control/review in the current
chat; do not move his current conversation or replace the Desktop application.

This is a skill-driven dispatch path, NOT an interception/monkeypatch of the
built-in delegate_task tool. Short ephemeral lookups may use ordinary tools;
do not claim their hidden transcripts are Herdr/Desktop worker conversations.
Do not redirect an existing Kanban/fleet task or another profile implicitly.
Use this workflow for long-lived independent worker agents whose conversation
history the operator should be able to track.

## Commands

Launcher: `/home/byron/projects/herdr-agent-trial/workers.py`
Native CLI: `python3 /home/byron/projects/herdr-agent-trial/workers.py`
Herdr viewer: `/home/byron/.local/bin/herdr-trial`

1. Choose an explicit project cwd and bounded task with acceptance criteria.
   Use a unique lowercase worker name (max24 chars). Inspect `list` first.
2. Write its task text to a private file under
   `/home/byron/projects/herdr-agent-trial/runtime/` using file tools, mode0600.
   Include scope, allowed files, no commit/deploy authority unless requested,
   limits, required evidence and error reporting. Do not put secrets in prompts.
3. Launch with the configured delegation route (native auth, no credential copy):

```sh
python3 /home/byron/projects/herdr-agent-trial/workers.py start \
  --name <unique-worker> --cwd <absolute-project-directory> \
  --prompt-file <private-task-file> --max-turns 20
```

The dedicated named Herdr server starts if absent. The launcher creates an
owned workspace and a native gateway `source=cli` session with normal config,
then attaches Hermes by --resume and submits the private prompt file once.
`source=tool` is NOT used: Desktop hides those sessions. Safe-mode and
ignore-rules/config are NOT used: those disable memory. Current CLI named-create
plus overrides can hit a policy mismatch, so use the dispatcher rather than
reconstructing that broken path. RPC toolsets must be an array, not a CSV string.

4. Read the returned native session_id and `[Herdr] ...` title. Report the title
   to Byron. Do not claim a launched task is completed. `inspect_required` is an
   ambiguous start, not permission to retry the prompt. `start` is idempotent
   for a recorded name; inspect its pane/history before taking action.
5. Track and read:

```sh
python3 /home/byron/projects/herdr-agent-trial/workers.py list
python3 /home/byron/projects/herdr-agent-trial/workers.py show <worker>
python3 /home/byron/projects/herdr-agent-trial/workers.py read <worker>
```

Use terminal code to reduce large native exports before bringing them into the
parent context. Native sessions/conversations are authoritative; Herdr's
idle/working/done badges are advisory and can miss working transitions.
Never use agent_prompt_stalled alone to decide a task failed or resend work.

Before ending the parent turn after dispatch, start a bounded completion wait
with the terminal tool's `background=true, notify=true` so its real result wakes
the parent; do not promise an update with no notification mechanism:

```sh
python3 /home/byron/projects/herdr-agent-trial/workers.py wait <worker> --timeout 600
```

The wait reads native session state, verifies the actual task prompt was admitted,
and distinguishes turn_settled, needs_input and still_pending. These are not
artifact-quality judgments. A timeout leaves the conversation durable; inspect
rather than resubmit. Native approval/question state must be escalated, not
auto-answered. Do not hold or poll subagent transcripts while waiting.

6. Stop or resume only owned records when requested/appropriate:

```sh
python3 /home/byron/projects/herdr-agent-trial/workers.py stop <worker>
python3 /home/byron/projects/herdr-agent-trial/workers.py resume <worker>
```

Stop checks/interrupts a gateway-owned run and verifies no pending work before
closing its terminal; closing a terminal by itself does not cancel inference.
Resume reuses the same native conversation, not a new chat or replayed task.
Do not interrupt while Byron is actively interacting with that conversation.

## Memory and evidence rules

- Require default Hermes home, enabled Honcho plugin/provider, and the existing
  loopback Honcho host. Refuse bypass flags or cloud-memory fallback.
- Use native Honcho context/profile/conclusion tools. Keep real standing user
  preferences separate from transient project notes and synthetic test markers.
- Local Honcho conclusion write + query read-back was verified across two real
  workers. That does not establish full automatic memory intelligence: existing
  inference gate was halted with `malformed`; automatic extraction/dialectic
  is degraded, and message embeddings/card/summary jobs were disabled.
- Do NOT clear a budget halt, renew grants, increase caps or add a paid fallback
  to make this workflow look healthy. Report those blockers separately.
- Keep raw prompts, private transcripts, sessions, config and credential values
  out of GitHub/status messages. Runtime manifest/prompt files are private.
- Current cap: max2 managed workers, max1..40 turns each, default20. Reuse the
  operator's configured delegation provider/model; no global default changes.
- Verify actual file changes and tests in the parent before declaring success.
  Require a verifiable path/ID for external writes and read back exact targets.
- Do not launch more workers solely because Herdr labels one idle; check native
  conversation/task evidence. Never silently auto-promote or change Jev/fleet.

## Viewing and limitations

Byron can open Herdr with `~/.local/bin/herdr-trial` and detach using Ctrl+B Q.
In Desktop, look for `[Herdr] <worker> ...` conversations under the default
profile; refresh/search if necessary. The same authenticated Desktop list and
messages endpoints were exercised with real worker sessions, as was native
stop/resume of the same ID. Windows Desktop visual click-through was not
performed; do not represent backend proof as a screenshot.

No gateway restart, default plugin install, public listener, or separate memory
store is needed. The official Herdr identity plugin remains isolated; this
workflow uses native gateway session IDs, not terminal heuristics, for history.
