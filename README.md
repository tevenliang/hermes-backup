# Hermes Agent 备份

本仓库包含 Steven Liang 的 Hermes Agent 配置完整备份。

## 包含内容

- `SOUL.md` — 核心定义（贾维斯是什么）
- `MEMORY.md` — 长期记忆与工作规范
- `USER.md` — 用户画像与偏好
- `HEARTBEAT.md`、`IDENTITY.md`、`DREAMS.md`、`TOOLS.md`、`AGENTS.md` — 系统配置
- `skills/` — 所有自定义 Skill（含 douyin-transcription、system-check、tavily-search 等）
- `scripts/` — 所有自定义脚本（含废弃版本，保证与本地一致）
- `cron/` — 定时任务配置
- `memories/` — 每日记忆文件

## 安全说明

- `CREDENTIALS.md`（含 App Secret、密码等）已排除，不在本仓库中
- `auth.json`、Cookie 文件、`cache/`、`logs/`、`sessions/` 等运行时数据已排除
- 如需恢复完整运行环境，请联系 Steven 重新配置凭证

## 注意事项

- `scripts/` 中的 `douyin_daily_v*.py`、`daily_finance_v*.py` 等为历史版本，非废弃——保留所有版本以确保和本地完全一致
- 如无特殊说明，所有 Skill 均为已验证可用的最新版本
