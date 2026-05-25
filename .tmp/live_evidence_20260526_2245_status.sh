#!/usr/bin/env bash
set -euo pipefail

cd /home/tn/projects/marketlens-strike

date -Is
ps -p 1191355,1205293 -o pid,ppid,sid,pgid,stat,etime,cmd || true
systemctl --user list-timers marketlens-live-evidence-20260526-2245-guard.timer --no-pager --all || true
crontab -l || true
ls -lt logs/live_evidence logs/live_evidence/manifests | head -100
