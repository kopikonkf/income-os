#!/usr/bin/env bash
set -euo pipefail
DIE_HOME="${DIE_HOME:-/srv/die}"
DIE_STATE_ROOT="${DIE_STATE_ROOT:-/var/lib/die}"
DIE_INSTALL_ROOT="${DIE_INSTALL_ROOT:-/opt/die}"
HERMES_HOME="${HERMES_HOME:-$DIE_STATE_ROOT/hermes/income-operator}"
HERMES_BIN="${HERMES_BIN:-$DIE_INSTALL_ROOT/hermes/venv/bin/hermes}"
SERVICE_USER="${HERMES_SERVICE_USER:-die-hermes}"
WORKDIR="$DIE_HOME/company/die-agents/hermes"
JOB_NAME="die-production-cycle-v1"
SCHEDULE='0 */3 * * *'
PLAYBOOK="$DIE_HOME/company/operations/PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1.md"

[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo E_ROOT_REQUIRED >&2; exit 2; }
[[ -x "$HERMES_BIN" ]] || { echo E_HERMES_BIN >&2; exit 2; }
[[ -f "$PLAYBOOK" ]] || { echo E_PRODUCTION_PLAYBOOK >&2; exit 2; }

PROMPT='Run exactly one DIE production-cycle tick using company/operations/PRODUCTION_CHAIN_OPERATING_PLAYBOOK_V1.md as the operating playbook. Continue an actionable unfinished production card before starting new work. Treat WAITING_FOUNDER_QC and READY_FOR_MANUAL_PUBLISH as PARKED_HUMAN_GATE: preserve them for Founder review but do not let them block an independent eligible seed on a later cadence slot. Start at most one new approved Object Atlas seed noun this tick. Generate per seed noun and manage/reuse Blueprint at family level. Reuse a still-valid fixed Blueprint; call Division01 only when semantic authoring/revision is actually required; call Executive only for a new/material family promotion or escalation, never as a per-image gate. Hermes owns Kanban/state and must dispatch bounded Worker jobs rather than doing Worker work itself. Use the currently available production provider (MUXIA or another explicitly configured provider) only within zero-spend existing authority. A provider completion is not complete until a real artifact exists on filesystem. Continue immediately through recovery/upscale when needed, metadata, rights/IP preflight, deterministic QA and QC; do not wait for the next 3-hour tick once a cycle has started. At WAITING_FOUNDER_QC / READY_FOR_MANUAL_PUBLISH park that cycle and consider Hermes autonomous responsibility complete for it; do not upload, submit, publish, spend, or perform account/credential actions without Founder authority. During this early operational phase use `hermes send --to telegram` to report PRODUCTION_STARTED, ARTIFACT_CREATED, QA_QC_UPDATE, WAITING_FOUNDER_QC, READY_FOR_MANUAL_PUBLISH, or an explicit FAILED/BLOCKED milestone with task id, stage and next action. A production tick is materially successful only if it starts a new seed cycle or durably advances an actionable cycle/artifact; re-reading an unchanged parked human gate is not success. If no material progress is possible, report PRODUCTION_TICK_NO_PROGRESS/BLOCKED with reason and next action; [SILENT] is forbidden for production ticks. Silent failure is forbidden. The atomic task graph remains the long-horizon engineering journey; unrelated unfinished nodes are not production blockers. Return a concise final cycle summary.'

if runuser -u "$SERVICE_USER" -- env HERMES_HOME="$HERMES_HOME" DIE_HOME="$DIE_HOME" DIE_STATE_ROOT="$DIE_STATE_ROOT" TERMINAL_CWD="$WORKDIR" "$HERMES_BIN" cron list --all | grep -Fq "$JOB_NAME"; then
  echo E_PRODUCTION_CRON_ALREADY_EXISTS >&2
  exit 3
fi

runuser -u "$SERVICE_USER" -- env HERMES_HOME="$HERMES_HOME" DIE_HOME="$DIE_HOME" DIE_STATE_ROOT="$DIE_STATE_ROOT" TERMINAL_CWD="$WORKDIR" "$HERMES_BIN" cron create "$SCHEDULE" "$PROMPT" --name "$JOB_NAME" --deliver telegram --workdir "$WORKDIR" --continuity

echo PRODUCTION_CRON_INSTALL=PASS
echo JOB_NAME="$JOB_NAME"
echo SCHEDULE="$SCHEDULE"
echo DELIVER=telegram
echo CONTINUITY=true
echo PLAYBOOK="$PLAYBOOK"
