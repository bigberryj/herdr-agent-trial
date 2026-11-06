# Herdr local agent trial

User-local Herdr **0.9.5** on bigbai, with a named `j5-herdr-trial` server,
disposable workspace and two real native Hermes CLI sessions. This repository
contains trial configuration and verified observations, not a fork of Herdr.

## Open it

In a terminal on bigbai:

```sh
herdr-trial
```

Alternatively run `~/.local/bin/herdr-trial`. Detach with **Ctrl+B, then Q**.
Run it again to reattach. The named server keeps its terminals running.
There is no reboot autostart. No TCP listener or remote-machine setup was added.

Currently the scout conversation is available, idle; the reviewer was deliberately
quit to verify stopping a single worker. Its pane is back at the shell prompt.

## Installation and provenance

The official Linux x86_64 release binary was downloaded without executing an
installer and verified against GitHub's release-asset SHA256 metadata:

- Release v0.9.5; publisher binary, not rebuilt locally.
- SHA256 `14d9e8bc8b4a9e0118d77c32266f76d461f09b40342eb23752960bd89f59929d`.
- Reviewed tag commit `2ecf19a92fc3a7fff75b6ce3655ef04f4625ec01` in
  upstream `herdrdev/herdr` (Apache-2.0).
- Binary `~/.local/lib/herdr/v0.9.5/herdr`; command symlinks under ~/.local/bin.
- Separate trial config is this repository's config.toml; update/manifest checks,
  sounds, history persistence and automatic agent restore disabled.
- Named Unix sockets in ~/.config/herdr/sessions/j5-herdr-trial, both mode0600.

Reinstall the pinned binary and links after cloning to
`~/projects/herdr-agent-trial` with `python3 install.py`. Existing mismatched
binaries/links are refused, not overwritten. No dependencies or root needed.

## What actually ran — November 6, 2026

- Two real Hermes agents detected as ready/idle; each answered its synthetic
  prompt: `SCOUT_READY` and `REVIEWER_READY`. Native OpenAI Codex auth was used
  by Hermes itself. No OAuth tokens were extracted, copied or handled by Herdr.
- Detach via Ctrl+B Q returned client exit0 while server and both worker PIDs
  remained alive. A second PTY attachment rendered the same workspace, then
  detached successfully. This is terminal-client evidence, not a screenshot.
- Scout was quit and **manually** restarted using its native Hermes `--resume`
  ID. A new prompt recalled `ORCHARD-742`; matched the standalone response line,
  not the token in the restored conversation preview. Total three inference
  prompts; no tool execution requested, agents launched with zero toolset.
- Reviewer quit independently; exact process read-back showed shell foreground,
  while scout stayed alive. No other agents/panes were stopped.
- Upstream Hermes integration asset tests: **3 tests, OK**. Plugin installed only
  in `runtime/hermes` for install verification; exact bytes match reviewed source.
- Default ~/.hermes/config.yaml and .env hashes were unchanged after testing.
- Runtime verification evidence: evidence/verification.json (synthetic only).

## Important findings / limits

**Herdr's `agent prompt --wait` returned `agent_prompt_stalled` for two prompts
which actually completed successfully.** The installed Hermes classic gateway
CLI does not expose the working transition that the bundled detection rules
expect. Never automatically resend that error: read the pane and verify first.
Idle/done badges are not proof of completion. Use it as a manually supervised
terminal workspace, not an authoritative agent scheduler yet.

The successful launch syntax on this installed Hermes is:

```sh
herdr-trial agent start scout --kind hermes --pane <actual-pane-id> -- \
  chat --cli --safe-mode --provider openai-codex -m gpt-6.1-sol-900k \
  -t '' --source tool --max-turns 2
```

Discover actual IDs from creation JSON; do not guess. `chat` is required before
arguments. `--run-budget` and custom `--source herdr-trial` were rejected by this
Hermes gateway. `tool` is a supported source and keeps trial traffic out of
operator collection. Safe mode and zero tools keep these synthetic tests small;
they are not examples of fully equipped coding workers.

The official integration writes plugins.enabled in the selected Hermes home.
We tested only a disposable home; production integration was deliberately NOT
enabled. The plugin reports resumable identity only, not working/blocked state.
Automatic resume after server restart/reboot and live blocked-state detection
are **not verified**. Manual native conversation resume is verified separately.

Desktop Konsole launched, but reported no outputs and computer-use found no
windows, so visual desktop proof is unavailable in this graphical session.
The terminal PTY interface was actually rendered and exercised. This trial did
not change display settings to manufacture a screenshot.

## Boundaries and rollback

No Telegram gateway restart, Jev/router policy change, default plugin install,
paid provider fallback, credential copying, dellmini/SSH/firewall or production
project edits. This is process/config separation, **not an OS sandbox**. Native
Hermes safe-mode sessions still exist in its normal session store, and an
explicitly resumed session reuses its frozen policy.

To stop only this trial, first save any new work, then:

```sh
herdr-trial session stop j5-herdr-trial --json
```

That stops this trial server and its panes; do not run it while work matters.
Remove only the two known symlinks, pinned binary directory and trial config
when uninstalling. The disposable integration has no production effects.

## Recommendation

Useful now as an optional visible multi-agent terminal workbench. Keep automatic
status-driven scheduling off. Next optional slice: reproduce/fix the new Hermes
CLI working-state detection, then separately trial production identity integration
and restart recovery with explicit scope. Do not replace current task routing.
