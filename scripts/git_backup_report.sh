#!/bin/bash
cd /root/.openclaw/workspace

# Sync scripts to workspace
/root/.openclaw/scripts/sync_all_to_workspace.sh > /tmp/sync_output.log 2>&1

# Git add
git add -A >> /tmp/sync_output.log 2>&1

# Check if there are changes to commit
if git diff --cached --quiet 2>/dev/null; then
    echo "No changes to commit" >> /tmp/sync_output.log
    exit 0
fi

# Get changed files
CHANGED=$(git diff --cached --name-only | head -10)
COUNT=$(git diff --cached --name-only | wc -l)

# Commit and push
git commit -m "Auto backup $(date '+%Y-%m-%dT%H:%M')" >> /tmp/sync_output.log 2>&1
git push origin main >> /tmp/sync_output.log 2>&1

# Send Feishu notification via Python for proper JSON handling
python3 << 'PYEOF'
import subprocess, json, urllib.request

# Get changed files
result = subprocess.run(['git', 'diff', '--cached', '--name-only'], capture_output=True, text=True)
files = result.stdout.strip().split('\n') if result.stdout.strip() else []
count = len(files)

# Build message
changed_str = '\n'.join([f'• {f}' for f in files[:10]])
if count > 10:
    changed_str += f'\n• ...还有{count-10}个'

msg = f"📦 **Git 备份完成**\n\n📁 变更文件 ({count} 个):\n{changed_str}\n\n⏰ 自动备份"

# Get Feishu token
req = urllib.request.Request(
    'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
    data=json.dumps({"app_id":"cli_a947b541d8785bd9","app_secret":"HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"}).encode(),
    headers={'Content-Type': 'application/json'}
)
with urllib.request.urlopen(req) as resp:
    token = json.load(resp)['tenant_access_token']

# Send message
msg_data = {
    "receive_id": "ou_d4b39b86c8715f79b2c5b070c4e55393",
    "msg_type": "text",
    "content": json.dumps({"text": msg})
}
req2 = urllib.request.Request(
    'https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id',
    data=json.dumps(msg_data).encode(),
    headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
)
with urllib.request.urlopen(req2) as resp:
    print(resp.read().decode())
PYEOF
