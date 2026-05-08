#!/bin/bash
# Sync cron jobs + scripts to workspace for git backup
# 1. Sync cron jobs.json
cp /root/.openclaw/cron/jobs.json /root/.openclaw/workspace/.cron-jobs-backup.json
# 2. Sync scripts directory (exclude __pycache__ and temp files)
rsync -a --exclude='__pycache__' --exclude='*.pyc' --exclude='*.bak' --exclude='*.log' --exclude='state.json' --exclude='douyin_content_cache.json' /root/.openclaw/scripts/ /root/.openclaw/workspace/scripts/
echo "All synced at $(date)"
