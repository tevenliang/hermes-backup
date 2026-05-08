---
name: getnote-sync
version: 1.2
description: |
  Get笔记增量同步任务。每小时自动执行（cron），从 GetNotes API 拉取最新笔记，
  过滤出未处理的笔记，生成 Markdown 文档写入飞书「400 贾维斯」文件夹，并更新状态文件防重。
  
  用户手动触发时说：「同步笔记」「Get笔记同步」「笔记同步」
---

# Get笔记同步 Skill（getnote-sync）

## 触发方式

- **手动触发**：用户说「同步笔记」「Get笔记同步」「笔记同步」
- **自动执行**：每小时 via cron（job: Get笔记每小时同步，schedule: `0 * * * *`）

---

## 执行方式

直接运行脚本，不分析不搜索不要解释：

```bash
python3 /Users/twliang/.hermes/skills/workspace/getnote-sync/scripts/getnote_sync.py
```

脚本会：
1. 从 GetNotes API 获取所有笔记（分页，从新到旧）
2. 过滤出不在 processed 列表中的笔记（新笔记）
3. 每条笔记生成 Markdown 内容
4. 用 lark-cli --as user 创建飞书文档
5. 更新状态文件

---

## 目标资产（MacBook 本机路径）

| 资产 | 路径 |
|------|------|
| 主脚本 | `~/.hermes/skills/workspace/getnote-sync/scripts/getnote_sync.py` |
| 状态文件 | `~/.hermes/scripts/getnote_state.json` |

**注意**：状态文件目录需存在（`mkdir -p ~/.hermes/scripts`），首次运行前确保文件存在。

---

## API 配置

| 字段 | 值 |
|------|-----|
| GetNotes API Key | `gk_live_c17ca17f43b3e387...` |
| GetNotes Client ID | `cli_3802f9db08b811f1...` |
| Feishu App ID | `cli_a97cf4a2bef8dcce`（当前 Hermes bot） |
| Bitable | `VNLrbIYoAausDOs5uovcO7fPn0d / tbl2vVHnujNPQczd` |
| 文档存放 | folder_token: `K312fSiL0lApa8dLCARczd1jnUO` |

---

## Bitable 追踪表

**Bitable 写入：正常工作（已验证）**

- **Bitable**: `VNLrbIYoAausDOs5uovcO7fPn0d` / table `tbl2vVHnujNPQczd`
- **写入方式**: `lark-cli api POST ... --as user`（用户身份，非 bot）
- **写入字段**: `文章标题`（类型：超链接，含 text + link）
- **API 端点**: `/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records`

> **注意**：三个核心 Bitable 资产必须严格区分，绝不能混用：
> - 知识库（本文档）: `VNLrbIYoAausDOs5uovcO7fPn0d` — getnote-sync 用这个
> - 客户数据: `BO6kb2c7haHY2FsLJCecH1mrnhe`
> - 账号密码及API: `OvQ2bpM6gaez1ksDTYwclTPjnib`
>
> **常见错误**：用 lark-mcp 工具（如 `mcp_lark_mcp_bitable_v1_appTableRecord_create`）读写时会受到 bot 权限限制，可能报 `91403 Forbidden` 或 `99991679`。正确做法是用 `lark-cli api ... --as user`。

## 触发方式

- **手动触发（当前默认）**：用户说「同步笔记」「Get笔记同步」「笔记同步」
- ~~每小时 cron~~：已暂停，改为手动执行

> **注意**：所有 cron 任务默认暂停，由用户手动触发词执行。如需恢复 cron，先确认用户意愿。

lark-cli 默认可能绑定旧 bot（`cli_a947b541d8785bd9`）。首次使用前执行：

```bash
echo "<新bot_app_secret>" | lark-cli config init --app-id cli_a97cf4a2bef8dcce --app-secret-stdin
lark-cli config show  # 验证 appId 已切换
```

### 2. lark-cli bitable 授权（重要）

lark-cli 的 bitable 操作使用 `base` domain，不是 `bitable`：

```bash
# 1. 发起 Device Flow 授权
lark-cli auth login --no-wait --domain base --json
# 输出: {"verification_url":"https://accounts.feishu.cn/oauth/v1/device/verify?flow_id=...","user_code":"XXXX-XXXX"}

# 2. 用户在浏览器打开 URL，输入 user_code 授权

# 3. 完成授权后执行（阻塞等待）
lark-cli auth login --device-code <device_code>
```

注意：lark-cli 的 user token 授权成功后，会获得 `base:*` scope，可读写 bitable；但与 lark-mcp 的 token 存储完全分开。

### 3. 凭证管理规范（重要）

**所有凭证必须优先从飞书多维表格读取，不要硬编码在脚本里，也不要重复告知。**

凭证查询流程：
```python
# 1. 从 Bitable 读取（app_token: OvQ2bpM6gaez1ksDTYwclTPjnib, table: tblvdLBUJJbOouUy）
# 2. 读到后写入 ~/.hermes/scripts/ 下的状态文件
# 3. 后续运行直接从状态文件读
```

---

## 注意

- **增量同步**：依赖状态文件 processed 列表防重，不依赖时间过滤
- **每小时执行**：整点执行（cron schedule: `0 * * * *`）
- **文档存放**：「400 贾维斯」文件夹（folder_token: `K312fSiL0lApa8dLCARczd1jnUO`）
- **用户身份**：使用 lark-cli --as user 创建文档
- **脚本内硬编码凭证**：更新时需同步修改脚本顶部的 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`（未来应改为从 Bitable 动态读取）
