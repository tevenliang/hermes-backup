# Bot Migration Procedure

When the feishu bot is rotated (old bot decommissioned, new bot takes over), update credentials in two places:

## 1. Runtime Config (most critical)
File: `~/.openclaw/openclaw.json`

```json
"channels": {
  "feishu": {
    "enabled": true,
    "appId": "cli_a97cf4a2bef8dcce",      // ← new bot id
    "appSecret": "BQEEuScBOAzPa0ywZBpJue4y5wOFuP55"  // ← new secret
  }
}
```

This is the **active runtime config** Hermes/OpenClaw reads at startup. Changes take effect on next gateway restart.

## 2. Hermes Memory
File: `~/.hermes/memories/USER.md`

Update the feishu credentials line:
```
飞书凭证:app_id cli_a97cf4a2bef8dcce, folder XwBif5LqOlW1oEdXBoYcx2ADnWe, bitable P4o3bUtsIaoUttsmIslcjEkunre
```

## 3. Workspace Scripts (grep and replace)

Find all scripts with hardcoded old bot credentials:
```bash
grep -r "cli_a947b541d8785bd9" ~/.hermes/scripts/
grep -r "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1" ~/.hermes/scripts/
```

Two replace patterns:
- `FEISHU_APP_ID = "cli_a947b541d8785bd9"` → `FEISHU_APP_ID = "cli_a97cf4a2bef8dcce"`
- `FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"` → `FEISHU_APP_SECRET = "BQEEuScBOAzPa0ywZBpJue4y5wOFuP55"`

Also in JSON payloads embedded in scripts (some scripts call auth API directly):
- `"app_id": "cli_a947b541d8785bd9"` → `"app_id": "cli_a97cf4a2bef8dcce"`

## 4. Restart Gateway (MacBook)
```bash
hermes gateway restart
```

## Notes
- Old bot id: `cli_a947b541d8785bd9`
- New bot id: `cli_a97cf4a2bef8dcce`
- Bot user_id in feishu remains the same (`ou_9409fb343970f30fd0adb6b3aed587d7`) — only app credentials change
- **macOS note**: Do NOT use `systemctl` — use `hermes gateway restart` instead
