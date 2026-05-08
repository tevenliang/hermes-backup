---
name: system-check
description: 系统检测 — 检查 OpenClaw 运行状态 + Minimax Coding Plan 用量 + 硬件健康状态（磁盘/CPU/内存），中文输出。
metadata: {"clawdbot":{"emoji":"🔍"}}
---

# 系统检测 Skill

同时检测 OpenClaw 运行状态、Minimax Coding Plan 用量和硬件健康状态，**中文输出**。

## 触发词

- "系统检测"
- "系统状态"
- "检查状态"

## 执行方式

AI 助手直接执行两个脚本合并输出：

1. **硬件健康检查** — 运行 `system-check.sh`（磁盘/CPU/内存/服务）
2. **Minimax 用量** — 运行 `minimax-check.sh`（API查询）
3. **OpenClaw 状态** — 调用 `session_status` 工具（直接读取，不走shell）

## 输出内容

### 模块一：OpenClaw 状态
- 🤖 当前模型
- 📥 Token（输入/输出）
- 💾 Cache 命中率
- 📚 Context 上下文占用（占用率 + 绝对值）
- 🧵 当前会话信息
- ⚙️ 运行时信息
- 🪢 队列深度
- 📊 额度剩余

### 模块二：Minimax Coding Plan（运行脚本）
- 📊 已用 / 总配额 prompts 及百分比
- 🔄 剩余 prompts 数量
- ⏱️ 重置时间
- 状态指示：
  - 💚 充足（< 50%）
  - 🟡 正常（50-80%）
  - 🔴 紧张（≥ 80%）
  - 🔴 紧急（≥ 90%）

## 脚本路径

### 模块三：硬件健康状态
- 💾 磁盘使用率
- ⚙️ CPU 负载（1分钟平均值）
- 🧠 内存使用率
- 状态指示：✅ 正常 / ❌ 告警

## 脚本路径

```
/root/.openclaw/workspace/skills/system-check/scripts/system-check.sh
/root/.openclaw/workspace/skills/system-check/scripts/minimax-check.sh
```

## 依赖

环境变量（已在 `/root/.openclaw/workspace/.env` 中配置）：
- `MINIMAX_CODING_API_KEY`
- `MINIMAX_GROUP_ID`

API 端点：`https://www.minimaxi.com/v1/token_plan/remains`
字段：`current_weekly_total_count` / `current_weekly_usage_count`
