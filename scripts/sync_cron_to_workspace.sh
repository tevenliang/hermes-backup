#!/bin/bash
# Sync OpenClaw cron jobs to workspace for git backup
cp /root/.openclaw/cron/jobs.json /root/.openclaw/workspace/.cron-jobs-backup.json
echo "Cron jobs synced at $(date)"
