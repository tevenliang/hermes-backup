category: productivity
---
name: feishu
description: "Feishu (飞书) operations: lark-cli, documents, bitables, cron, and operational rules for this user's primary work channel"
triggered_by: "any task involving 飞书, Feishu, lark-cli, 贾维斯飞书操作, or the user's feishu channel"
title: "Feishu Operations"
version: "1.0"
---

# Feishu Operations

Feishu is the primary operational channel for this user. All document creation, bitable writes, and cron-driven notifications flow through feishu.

## Lark-cli (Primary Interface)

All Feishu document and bitable operations must use `lark-cli`. **Never** generate `.md` files as attachments or use raw Feishu APIs directly when lark-cli is available.

### Core Commands

```bash
# Document operations
lark-cli doc create --parent-token <folder_token> --title "<title>" --content "<content>"
lark-cli doc update --doc-token <token> --content "<content>"

# Bitable operations  
lark-cli bitable create --parent-token <folder_token> --title "<title>"
lark-cli bitable record add --app-token <app_token> --table-id <table_id> --fields '<json>'

# User identity (docs belong to user vs bot)
lark-cli --as user ...   # Steven's identity
lark-cli --as bot ...    # Bot identity for automation
```

### Lark-cli Path Rule
Use **workspace-relative paths** with `@` prefix + `cwd=WORKSPACE`:
```bash
lark-cli doc create ... @skills/my-skill/output.md cwd=WORKSPACE
```

---

## Document Conventions

### Folder Structure
- All documents stored in the **「400 贾维斯」** folder
- **folder_token**: `K312fSiL0lApa8dLCARczd1jnUO`

### Title Format
```
主题 日期 时间
例: 多Session工作讨论 2026-04-26 14:57
```
Exception: Get笔记同步 → use original title, no prefix, no date.

### Link Format
```
[查看原文](url)
```
This is a **global mandatory standard** — URL hidden as clickable blue link.

### Block Type Rules
- **Forbidden**: `make_bullet()` — creates bullet lists that render incorrectly
- **Required**: `make_text()` for all summary text; lines starting with `- xxx` have the prefix stripped before writing

---

## Bitable (Multi-dimensional Table)

### 三个核心 Bitable 资产（必须严格区分）

| 名称 | app_token | table_id | 用途 |
|---|---|---|---|
| **知识库** | `VNLrbIYoAausDOs5uovcO7fPn0d` | `tbl2vVHnujNPQczd` | getnote-sync 同步笔记追踪 |
| **客户数据** | `BO6kb2c7haHY2FsLJCecH1mrnhe` | `tblDEBAW1NOq61Ch` | 客户信息管理 |
| **账号密码及API** | `OvQ2bpM6gaez1ksDTYwclTPjnib` | `tblvdLBUJJbOouUy` | 账号密码查询 |

> **写入方式**：所有 bitable 写入必须用 `lark-cli api POST ... --as user`（user identity），不能用 lark-mcp 工具（后者用 bot token，会报 `91403 Forbidden` 或 `99991679`）。正确格式见下方 API 调用示例。

### ⚠️ lark-cli 的 App 身份跨组织权限问题（关键）

lark-cli 当前绑定的飞书应用 `cli_a97cf4a2bef8dcce` 属于 **hermes 组织**，而用户 Steven 的账号 (user_id 394491) 在**另一个组织**。

| 操作 | 权限状态 |
|---|---|
| 读取用户所在组织的文档/多维表格 | ❌ 无权（app 不属于该组织） |
| 写入用户所在组织的多维表格 | ❌ 同上 |
| 在 hermes 组织内操作 | ✅ 可以（app 属于该组织） |

**症状**：lark-cli base/record 查询返回 `permission denied` 或 `99991679 service unavailable`

**解法**：
1. 用户在飞书开放平台（open.feishu.cn）将 `cli_a97cf4a2bef8dcce` 应用添加到自己所在组织
2. 在应用权限管理中补充 `bitable:app`（应用级多维表格权限）
3. 或者：换用用户身份认证（Device Flow），确保 `--as user` 时用的是用户本人在**自己组织**内的身份

**验证**：在飞书开放平台 → 应用管理 → `cli_a97cf4a2bef8dcce` → 权限管理，检查是否有 `bitable:app`。如果看不到该组织，说明应用未被添加到该组织。

### lark-cli 与 lark-mcp Token 独立性（关键）

这是两个完全独立的认证体系，配置互不影响：

| | lark-cli | lark-mcp |
|---|---|---|
| Token 存储 | `~/.lark-cli/config.json` | `config.yaml` mcp_servers.lark-mcp |
| 身份 | `--as user`（Steven）| Bot（cli_a97cf4a2bef8dcce）|
| 用途 | 脚本内 bitable 写入、文档创建 | 实时 MCP 工具调用 |
| 权限范围 | 依赖 Device Flow 授权时 grant 的 scope | 依赖飞书开放平台给 bot 配置的权限 |

**踩坑记录**：调试 bitable 写入时用 lark-mcp 工具测试 `OvQ2bpM6gaez1ksDTYwclTPjnib` 报 `91403 Forbidden`——不是因为权限不够，是因为 lark-mcp 用的是 bot 身份对这个 bitable 没有写权限。脚本里正确用的是 `lark-cli api ... --as user`。

**Bitable domain 是 `base`，不是 `bitable`**：Device Flow 授权时用 `--domain base`。

### 正确 API 调用格式

```bash
# 创建飞书文档（lark-cli）
lark-cli docs +create --title "标题" --markdown @tmp.md --as user --folder-token XwBif5LqOlW1oEdXBoYcx2ADnWe

# 写入 bitable（必须用 --as user，切忌用 lark-mcp）
lark-cli api POST /open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records \
  --data '{"fields":{"文章标题":{"text":"标题","link":"url"}}}}' \
  --as user
```

---

## Channel Configuration

```json
"feishu": {
  "enabled": true,
  "appId": "cli_a97cf4a2bef8dcce",
  "appSecret": "BQEEuScBOAzPa0ywZBpJue4y5wOFuP55",
  "domain": "feishu",
  "groupPolicy": "open",
  "connectionMode": "websocket",
  "webhookPath": "/feishu/events",
  "dmPolicy": "pairing",
  "allowFrom": ["ou_d4b39b86c8715f79b2c5b070c4e55393"]
}
```

> **Config location**: The runtime feishu channel config lives in `~/.openclaw/openclaw.json`, NOT `~/.hermes/config.yaml`. Hermes reads it from the OpenClaw runtime store. Edit `~/.openclaw/openclaw.json` directly for runtime credential changes.

### DM Policy Red Line
`dmPolicy` **must never** be changed to `allowlist`. 
- `pairing` = can actively send messages to paired users ✓
- `allowlist` = blocks all feishu messages ✗

### User IDs
- Steven's Feishu DM: `ou_d4b39b86c8715f79b2c5b070c4e55393`
- Current session (Javis DM): `ou_9409fb343970f30fd0adb6b3aed587d7`

---

## Cron Integration

Standard cron parameters for feishu output:
```bash
--session isolated --announce --channel feishu --to ou_d4b39b86c8715f79b2c5b070c4e55393
```

- `isolated + agentTurn` = timed AI task (recommended)
- `main + systemEvent` = system events only, no tool calls

---

## Image Handling

When user shares screenshots/images in Feishu, use the model's native multimodal capability (MiniMax M2.7 支持图片输入)，直接描述图片内容。

图片发来时用模型原生多模态能力处理，不需要额外工具。

## Pitfalls

1. **Never** use `make_bullet()` for feishu doc content — use `make_text()` instead
2. **Never** generate `.md` attachments — always use lark-cli to create docs directly
3. **Never** change `dmPolicy` to `allowlist` — it blocks all incoming messages
4. **Always** use the exact folder_token `K312fSiL0lApa8dLCARczd1jnUO` for document storage
5. **Always** use `[查看原文](url)` link format in documents
6. **Bot migration**: When the feishu bot is replaced, update BOTH `~/.openclaw/openclaw.json` (runtime config, `channels.feishu.appId/appSecret`) AND all scripts that hardcode `FEISHU_APP_ID` / `FEISHU_APP_SECRET` constants. Search workspace for old app_id to find all script locations.
7. **Gateway restart on macOS**: Always use `hermes gateway restart` — do NOT use `systemctl --user restart` (Linux-only). Using the wrong command leaves the old gateway process running, causing "Another local Hermes gateway is already using this Feishu app_id" errors on the next restart attempt.
