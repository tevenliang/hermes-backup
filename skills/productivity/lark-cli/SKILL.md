---
name: lark-cli
description: 飞书官方 CLI 工具（lark-cli），用于飞书文档/多维表格/云盘/日历/消息等所有飞书内容的创建、读取、编辑和管理。当用户提及飞书文档、云文档、多维表格、飞书日历、飞书消息等操作时优先使用本 Skill。
version: 1.1.0
---

# 飞书 CLI (lark-cli)

## 核心定位
飞书官方 CLI 工具，v1.0.17+。**飞书操作统一用 lark-cli，feishu-mcp 已废弃（token 频繁过期）**。

**优先级**：`lark-cli`（稳定，device code 自动续期） > `feishu-mcp`（已弃用）

**关键警告**：`lark-cli` 和 `lark-mcp` 使用**完全独立的 token 存储**，配置互不影响。lark-cli 的 auth/token 与 MCP server 的 bot token 是两套系统。**推荐始终使用 lark-cli。**

---

## ⚠️ 已知陷阱

### 1. feishu-mcp 已废弃，切换到 lark-cli
- lark-mcp / feishu-mcp token 频繁过期，恢复需要 OAuth 浏览器回调（localhost:3000），极麻烦
- 2026-05-06 起所有飞书操作强制使用 lark-cli，禁止使用 lark-mcp
- 参考：https://github.com/larksuite/cli

### 2. bitable 对应 domain 是 `base`，不是 `bitable`
- `lark-cli auth login --domain bitable` → unknown domain
- 正确：`lark-cli auth login --domain base`（bitable 在飞书 API 体系里叫 base）
- Device Flow 授权完成后，user token 拥有 `base:*` scope，可读写多维表格

### 3. 多维表格（bitable/base）操作命令格式
`lark-cli base +record-list` 格式**不是真实命令**。
真实调用方式统一用 `lark-cli api`：
```bash
# 读记录
lark-cli api GET /open-apis/bitable/v1/apps/<app_token>/tables/<table_id>/records \
  --params '{"page_size":5}' --as bot --format ndjson

# 写记录
lark-cli api POST /open-apis/bitable/v1/apps/<app_token>/tables/<table_id>/records \
  --data '{"fields":{"账号描述":"test","类型":"APIKEY"}}' --as bot --format json
```

### 4. Bot 读 vs 写 bitable 权限
- Bot 身份**可以读** bitable（`--as bot`）
- Bot 身份**无法写** bitable（`91403 Forbidden`）——除非在飞书开放平台给 bot app 手动开通 bitable 写入权限
- 如需 bot 写权限：在飞书开放平台 → 应用功能 → 权限管理 → 添加 `bitable:app` 写权限并重新发布

### 5. App 本身需要 bitable:app 权限（不仅仅是用户授权）
- 即使用 `--as user` + Device Flow 授权后仍报 `99991679`，原因是**应用** `cli_a97cf4a2bef8dcce` **本身没有被管理员添加到该 bitable 的访问权限**
- 解决：需要企业管理员在飞书开放平台 → 应用 `cli_a97cf4a2bef8dcce` → 权限管理 → 添加 `bitable:app`（多维表格权限），然后重新发布应用
- **仅重新授权 Device Flow 不能解决此问题**，必须给应用本身开通权限

### 6. lark-cli base +record-list 不支持服务端过滤
- lark-cli base 命令不支持 --filter 参数，无法在服务端过滤
- 解决：读回全表记录后，用 grep/jq 按关键词过滤字段

---

## 安装状态
- 路径：`/Users/twliang/.local/bin/lark-cli`（MacBook 本机）
- 版本：`lark-cli version 1.0.17`（可更新至 1.0.23）
- 配置：`/Users/twliang/.lark-cli/config.json`（app_id: `cli_a97cf4a2bef8dcce`）

## 用户认证（Device Flow）

脚本使用 `--as user` 时需要用户已完成 Device Flow 授权。

### 授权流程
```bash
# 1. 发起 Device Flow（返回 verification_url 和 user_code）
lark-cli auth login --no-wait --domain base --json

# 2. 用户在浏览器打开 verification_url，输入 user_code 完成授权

# 3. 立即执行以下命令（阻塞直到用户授权或超时）
lark-cli auth login --device-code <device_code> --json
```

### 所需 Scope（自动申请）
`base:record:read` `base:record:create` `base:record:update` `base:record:delete` 等。

### 身份规则
- `--as user`（默认）：用 Steven 用户身份，文档归属用户本人 ✅
- `--as bot`：用 bot 身份，适合自动化任务
- user 身份 = 你本人干活，文档归你；bot 身份 = AI 打工，文档归 bot

## 常用命令速查

### 📄 飞书文档（docs）
```bash
# 创建文档（支持 Markdown）
lark-cli docs +create --title "文档标题" --markdown @file.md --folder-token K312fSiL0lApa8dLCARczd1jnUO --as user

# 读取文档内容
lark-cli docs +fetch --doc-token <doc-token>

# 搜索文档
lark-cli docs +search --query "关键词"
```

### 🗃️ 多维表格（base）

```bash
# 列出表格所有记录
lark-cli base +record-list --base-token <app-token> --table-id <table-id> --as user

# 列出表格所有字段（含字段ID和类型）
lark-cli base +field-list --base-token <app-token> --table-id <table-id>

# 批量创建记录（正确格式）
lark-cli base +record-batch-create \
  --base-token <app-token> \
  --table-id <table-id> \
  --as user \
  --json '{"fields":["字段1","字段2"],"rows":[["值1","值2"],["值3","值4"]]}'
```

**`--json` 格式说明**：
- 顶层 key 必须是 `fields`（字段名数组）和 `rows`（二维值数组）
- `--records` 不是有效 flag，错误信息 `required flag "json" not set` 表示你需要用 `--json`
- 字段值：文本用字符串，数字直接写数字（如 `100`），单选写字符串 `"抖音"`，日期写毫秒时间戳 `1745404800000`

**创建字段**：
```bash
lark-cli base +field-create \
  --base-token <app-token> \
  --table-id <table-id> \
  --as user \
  --json '{"name":"字段名","type":"text"}'
```
type 可选值：`text` | `number` | `single_select` | `multiple_select` | `date` | `user` | `file` | `lookup` 等。

### 📁 云盘（drive）
```bash
# 创建文件夹
lark-cli drive +create-folder --name "文件夹名" --folder-token <parent-folder-token>

# 移动文件
lark-cli drive +move --file-token <doc-token> --folder-token <target-folder-token>
```

### 📅 日历（calendar）
```bash
# 查看日历日程
lark-cli calendar +agenda

# 创建日程
lark-cli calendar events create --params '{"summary":"会议标题","start_time":...}'
```

### 💬 消息（im）
```bash
# 发送消息
lark-cli im messages create --data '{"receive_id":"ou_xxx","msg_type":"text","content":"..."}'
```

### 🔍 诊断
```bash
# 健康检查
lark-cli doctor
```

## 关键参数说明
| 参数 | 说明 |
|------|------|
| `--as user|bot` | 身份类型，默认 user |
| `--dry-run` | 仅打印请求不执行 |
| `--format json|table|csv` | 输出格式，默认 json |
| `--page-all` | 自动翻页获取所有数据 |
| `--jq <expr>` | 用 jq 表达式过滤输出 |

## 核心Bitable资产

Steven 的三个核心 bitable，**每次操作前必须确认目标表格**：

| 名称 | app_token | table_id | 用途 |
|---|---|---|---|
| 账号密码及API | `OvQ2bpM6gaez1ksDTYwclTPjnib` | `tblvdLBUJJbOouUy` | 账号密码管理 |
| 内容追踪 | `NeDBbyQvTa0xdysDCbRcQZ8cnMf` | 博主链接 `tbl9cnCB9Hnjxuzb` / 文章内容 `tbllE5S5vOhj5W9x` | 抖音/小红书/公众号博主文章追踪 |
| 知识库 | `VNLrbIYoAausDOs5uovcO7fPn0d` | `tbl2vVHnujNPQczd` | getnote-sync 同步笔记追踪 |
| 客户数据 | `BO6kb2c7haHY2FsLJCecH1mrnhe` | `tblDEBAW1NOq61Ch` | 客户动态跟踪 |

## 创建文档规范（必须遵守）

**创建飞书文档时，必须同时满足以下两点，否则用户无法直接编辑：**

1. **身份**：`--as user` 必须显式传入（文档归属用户本人）
2. **文件路径**：`--markdown @file.md` 要求**相对路径**且必须在 cwd 内
   - 绝对路径 `/tmp/skills-list.md` → 报错 `invalid file path`
   - 解决：先 `cd /tmp`，再用 `@skills-list.md`（相对路径）

**正确流程：**
```bash
# Step 1: 写临时文件
write_file --path /tmp/my-doc.md --content "..."

# Step 2: 创建文档（--as user + 正确 folder token）
cd /tmp && lark-cli docs +create \
  --title "文档标题" \
  --markdown @my-doc.md \
  --folder-token K312fSiL0lApa8dLCARczd1jnUO \
  --as user
```

---

## 触发场景
- 用户说"创建飞书文档"、"新建文档"
- 用户说"写入多维表格"、"更新记录"
- 用户说"搜索飞书文档"
- 用户说"获取日历日程"
- 用户发来飞书文档链接并要求读取内容
- **任何涉及飞书内容的操作**（强制使用 lark-cli）

## 禁止事项
- ❌ 禁止直接调用 `https://open.feishu.cn/open-apis/...` 原生 API（统一走 `lark-cli`）
- ❌ 禁止用 feishu-mcp / lark-mcp 执行飞书操作（token 频繁过期，已废弃）
- ❌ 禁止用 MCP 工具创建飞书文档（创建后文档归属 bot，用户无法编辑）
- ❌ 禁止生成 .md 文件后作为附件发送（必须用 `lark-cli docs +create --markdown @file.md` 直接创建飞书文档）