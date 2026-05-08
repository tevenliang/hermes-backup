---
name: system-check
description: >
  Use when asking for a full system health check: "全面检测"、"系统状态"、"检查状态"、
  "系统检测"、"硬件状态"、"Hermes状态"。

  Runs three independent checks: Hermes/runtime status, Minimax Coding Plan
  quota, and Mac hardware health (CPU/memory/disk). Output in Chinese with color indicators.
version: "1.0.0"
author: Steven Liang
license: MIT
allowed-tools: terminal,read_file
metadata:
  hermes:
    tags: [system, health-check, monitoring, hardware]
    related_skills: [daily-finance, getnote-sync, todo-management]
---

# 系统全面检测 Skill

## Overview

三模块健康检测，合三为一：
1. **Hermes 运行状态** — 模型连接、会话数、缓存状态
2. **Minimax Coding Plan 用量** — 5h 窗口 + 本周配额，彩色状态指示
3. **Mac 硬件健康** — CPU / 内存 / 磁盘，带阈值告警

触发词：「全面检测」「系统状态」「检查状态」「系统检测」

## When to Use

- 用户说"全面检测"、"系统状态"、"检查一下状态"
- cron 定时健康巡检（建议配合 `cronjob` 每日一次）
- 排除故障前先确认系统基础状态

## 执行方式

三个模块完全独立，并行执行，最终汇总输出：

### 模块一：Hermes 运行状态

通过 `hermes status` 和 `hermes insights` 读取实时数据，包括：
- 模型 / Provider
- Gateway 进程状态
- 活跃 Job 数、活跃 Session 数
- 累计 Session 数、Message 数（来自 `~/.hermes/state.db`）
- Token 用量统计（历史 30 天累计，本地 SQLite 记录，非 MiniMax API 返回）

### 模块二：Minimax Coding Plan 用量

```bash
# 脚本位置: ~/.hermes/skills/system/system-check/scripts/minimax-check.sh
# 直接运行，无需参数
bash ~/.hermes/skills/system/system-check/scripts/minimax-check.sh
```

**环境依赖**：`.env` 中需有 `MINIMAX_CODING_API_KEY`

**输出示例**：
```
📊 当前5h窗口: 45 / 5000 prompts (0%)
🔄 剩余: 4955 prompts
📅 本周配额: 312 / 50000 (0%)
📅 本周剩余: 49688 prompts
状态: 💚 充足 — 当前周期低于50%
```

### 模块三：Mac 硬件健康

```bash
# 脚本位置: ~/.hermes/skills/system/system-check/scripts/system-check.sh
# macOS 专用，内存计算与 Activity Monitor 一致
# 阈值: CPU 80%, 内存 85%
bash ~/.hermes/skills/system/system-check/scripts/system-check.sh
```

**重要**：此脚本 macOS only，不支持 Linux。

**输出示例**：
```
[2026-05-05 11:30] ✓ CPU: 23.5% | 内存: 61.2% | 无异常
```

---

## 快速执行脚本（推荐）

已有合三为一的主脚本：

```bash
bash ~/.hermes/skills/system/system-check/scripts/system-check.sh
```

**注意**：旧版主脚本存在 Linux/macOS 兼容性问题（`free -h` 为 Linux 命令）。macOS 用户请直接分别运行模块二和模块三，或使用下方的"完整并行执行"命令。

### 完整并行执行（最优）

```bash
{
  echo "=== Minimax 用量 ==="
  bash ~/.hermes/skills/system/system-check/scripts/minimax-check.sh
  echo ""
  echo "=== Mac 硬件健康 ==="
  bash ~/.hermes/skills/system/system-check/scripts/system-check.sh
} 2>&1
```

## 输出格式

**直接贴 system-check.sh 原始输出，不做 summary，不使用代码块，直接以纯文本形式输出在对话框内。**

输出内容示例：
```
==========================================
  系统检测 — 2026-05-06 16:32
==========================================

📦 Hermes 运行状态
------------------------------------------
  🤖 模型: MiniMax-M2.7 /MiniMax (China)
  🚀 Gateway: ✓
  📅 活跃Job: 1
  💬 活跃Session: 3
  📊 累计Session: 96 | Message: 7,210
  🔢 Token用量: 输入 18,931,108 | 输出 907,369 | 合计 224,763,674

📊 Minimax Coding Plan 用量
------------------------------------------
📊 当前5h窗口: 362 / 1500 prompts (24%)
🔄 剩余: 1138 prompts
📅 本周配额: 5482 / 15000 (36%)
📅 本周剩余: 9518 prompts
状态: 💚 充足 — 当前周期低于50%

🖥️  硬件健康状态 (macos)
------------------------------------------
  💾 磁盘: 10% / 468G
     ✅ 正常
  ⚙️  CPU: 11.4% (user+sys)
     ✅ 正常
  🧠 内存: 57.3% (active+wired+compressed)
     ✅ 正常

==========================================
  ✅ 检测完成 — 2026-05-06 16:32
==========================================
```

## 环境要求

| 模块 | 依赖 | 位置 |
|------|------|------|
| Minimax 用量 | `MINIMAX_CODING_API_KEY` in `.env` | `~/.hermes/.env` |
| 硬件健康 | macOS + `vm_stat` | 内置 |

## 已知问题 / 陷阱

1. **macOS 内存计算不能照搬 Linux**：macOS 的 `free -h` 不存在，内存口径与 Linux 完全不同（详见 `references/macos-memory.md`）。已统一使用 `vm_stat` 算法，与 Activity Monitor 一致。
2. **macOS 无 `bc` 命令**：脚本已改用 `awk` 替代，保留此条作为历史记录。
3. **Minimax API 限速**：调用间隔建议 ≥ 30s，频繁查询可能触发 429。
4. **hermes insights 调用开销**：约 0.5–1s，每次检测会计入统计（详见 `references/hermes-insights-parsing.md`）。
5. **⚠️ Skill 目录迁移后 cron job prompt 不会自动同步（高危）**：skill 绑定到 cron job 后，`cronjob update --prompt` 里的脚本路径不会随着 skill 目录迁移而自动更新。操作顺序必须是：① 迁移 skill 文件夹；② 更新 skill 内部 SKILL.md 的路径引用；③ 同时更新所有引用该 skill 脚本路径的 cron job prompts。验证方法：迁移后立即执行 `hermes skills list` 确认 skill enabled，再用 `cronjob list` 检查 prompt_preview 里的路径是否已更新为新路径。旧 prompt 里的 `~/.hermes/scripts/pc-health-check.sh` 即使 skill 已迁移也会继续存在，导致 cron 实际调用失败。

## 常见错误处理

| 错误 | 原因 | 解决 |
|------|------|------|
| `MINIMAX_CODING_API_KEY: unbound variable` | .env 未加载 | 在 shell 中先 `source ~/.hermes/.env` |
| `vm_stat: command not found` | 非 macOS 系统 | 硬件模块在 Linux 上跳过 |
| API 返回 `status_code: 10002` | API Key 无效/过期 | 更新 `MINIMAX_CODING_API_KEY` |
| `bc: command not found` | macOS 默认无 bc | `brew install bc` |

## cron 定时配置

建议每日 9:00 巡检：
```
cronjob create "全面检测" --prompt "执行 system-check skill，全面检测系统状态，输出到 origin" --schedule "0 9 * * *" --name "每日系统检测"
```

## 技术参考

- `references/mac-health-commands.md` — macOS 内存/CPU 检测技术细节（vm_stat 算法、awk 浮点比较、top 命令）
- `references/hermes-insights-parsing.md` — hermes insights 输出格式注意（Input/Output 在同一行的解析陷阱）
- `references/macos-memory.md` — macOS 与 Linux 内存计算差异（inactive 不算占用）
- `references/douyin-transcribe.md` — Douyin 视频转录：cookie 方案失败原因、agent-browser 方案、whisper 备选方案

## 相关 Skills

- `daily-finance`：每日财经汇总（定时任务，可与本 skill 共享 cron 时间窗口）
- `getnote-sync`：Get笔记增量同步
- `todo-management`：任务管理
