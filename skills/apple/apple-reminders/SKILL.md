---
name: apple-reminders
description: "Apple Reminders via remindctl: add, list, complete."
version: 1.1.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Reminders, tasks, todo, macOS, Apple]
prerequisites:
  commands: [remindctl]
---

# Apple Reminders

Use `remindctl` to manage Apple Reminders directly from the terminal. Tasks sync across all Apple devices via iCloud.

## Prerequisites

- **macOS** with Reminders.app
- Install: `brew install steipete/tap/remindctl`
- Grant Reminders permission when prompted
- Check: `remindctl status` / Request: `remindctl authorize`

## When to Use

- User mentions "reminder" or "Reminders app"
- Creating personal to-dos with due dates that sync to iOS
- Managing Apple Reminders lists
- User wants tasks to appear on their iPhone/iPad

## When NOT to Use

- Scheduling agent alerts → use the cronjob tool instead
- Calendar events → use Apple Calendar or Google Calendar
- Project task management → use GitHub Issues, Notion, etc.
- If user says "remind me" but means an agent alert → clarify first

## Quick Reference

### View Reminders

```bash
remindctl                    # Today's reminders
remindctl today              # Today
remindctl tomorrow           # Tomorrow
remindctl week               # This week
remindctl overdue            # Past due
remindctl all                # Everything
remindctl 2026-01-04         # Specific date
```

### Manage Lists

```bash
remindctl list               # List all lists
remindctl list Work          # Show specific list
remindctl list Projects --create    # Create list
remindctl list Work --delete        # Delete list
```

### Create Reminders

```bash
remindctl add "Buy milk"
remindctl add --title "Call mom" --list Personal --due tomorrow
remindctl add --title "Meeting prep" --due "2026-02-15 09:00"
```

### Complete / Delete

```bash
remindctl complete 729E072D         # Complete by JSON ID
remindctl delete 729E072D --force   # Delete by JSON ID
```

### Output Formats

```bash
remindctl today --json       # JSON for scripting
remindctl today --plain      # TSV format
remindctl today --quiet      # Counts only
```

## Date Formats

Accepted by `--due` and date filters:
- `today`, `tomorrow`, `yesterday`
- `YYYY-MM-DD`
- `YYYY-MM-DD HH:mm`
- ISO 8601 (`2026-01-04T12:34:56Z`)

## 完成提醒的标准流程（必须按顺序执行）

**触发条件**：用户说"已完成"、"完成了"、"done"、或提供了完成方式的备注

**Step 1**: 找到提醒的 JSON ID（用 `remindctl list <list名> --json` 或 `remindctl today --json`）
**Step 2**: 添加备注：`remindctl edit <id> --notes "备注内容"`（仅当用户提供了备注时才执行）
**Step 3**: 标记完成：`remindctl complete <id>`

## 分类体系（全部 Reminders 列表）

Steven 的提醒分为 **5 个列表**，所有输出按此顺序排序：

| 优先级 | 列表名 | 说明 |
|--------|--------|------|
| 1 | 工作 | 工作任务 |
| 2 | 学习 | 学习/研究任务 |
| 3 | 生活 | 生活事务 |
| 4 | 其他 | 周期性任务（周报、还款等） |
| 5 | 提醒 | 无分类的零散提醒 |

**输出排序规则**：先按列表优先级，再按截止日期（有截止日期的排前面）。

**注意**：「全部待办」默认指未完成任务，不需要已完成的 2000+ 条历史数据。

**凡是对提醒事项做任何改动（完成、延期、改备注、改标题等），完成后必须输出当前今日待办完整列表（`remindctl today`）。**

## 创建提醒的标准流程

### 自动分类规则

**触发条件**：用户说"提醒我xxx"、"创建待办xxx"、"新增任务xxx"，或表达任何新建提醒的意图

**判断逻辑（无需询问，直接执行）**：
- **工作**：工作项目、客户相关、会议/汇报、职场沟通、工具配置、职场人脉等 → `--list 工作`
- **学习**：技术研究、学习课程、代码开发、数据分析、投资研究、读书/课程等 → `--list 学习`
- **生活**：日常起居、购物、健康运动、娱乐休闲、家庭事务、旅游出行、社交娱乐等 → `--list 生活`
- **无法判断**：泛化描述（如"某件事"、"处理一下"）或跨类别模糊内容 → 不指定 list，直接创建

**常见判断示例**：
| 任务 | 分类 |
|------|------|
| 研究某技术/产品 | 学习 |
| 配置开发环境 | 工作 |
| 准备会议/汇报 | 工作 |
| 健身、跑步 | 生活 |
| 买菜、购物 | 生活 |
| 看病、体检 | 生活 |
| "处理一下xxx"（不明确） | 不指定list |

### 执行

1. 根据上述规则判断分类
2. `remindctl add "任务名" --list <分类>`（有分类时，不加截止时间）
3. `remindctl add "任务名"`（无法判断时，不指定list，不加截止时间）
4. **只有用户明确说了日期时才加 `--due`**

## 查找提醒

- `remindctl today` — 今日所有列表的提醒
- `remindctl list <list名>` — 查看特定列表
- **始终用 JSON ID 操作**：数字索引在不同列表间会重置，不可靠。用 `remindctl list <list> --json` 查真实 ID。

## 输出格式规范

**触发条件**：用户请求"全部待办"、"所有待办"、"全部任务"时

**必须遵守以下规则（逐项检查）：**

1. **默认只展示未完成任务**：`remindctl all` 输出含 `[x]` 已完成和 `[ ]` 未完成，必须用 `grep "\[ \]"` 过滤出未完成项再展示
2. **按分类排序输出**：先按分类（工作 > 学习 > 生活 > 其他 > 提醒）分组，再在每个分类内按截止日期排序（有截止日期的排前面）
3. **表头格式**：`| # | 任务 | 分类 | 截止日期 |`，紧凑排列，不做装饰性铺垫
4. **数量标注**：标题写"全部待办（共 X 条）"，X 是未完成数量，不是 all 总数

**"今日待办"执行步骤：**
```bash
remindctl all 2>&1 | grep "\[ \]" | grep "2026年5月6日"
```
- 只过滤 `[ ]` 未完成
- 只过滤当天日期
- 按分类排序输出

**错误示范**：把已完成条目混入输出、输出总数而非未完成数、不按分类排序。

## 其他规则

1. **提醒触发**：用户说"提醒我xxx" → 直接调用 remindctl，不需要每次询问
2. **Cron 仅在明确请求时**：只有用户明确说"定时任务"或"cron"时才创建 cron 任务

## 已知限制

- remindctl 支持 `--notes` 参数存放备注内容，标题保持不变

## 常见错误

- **问"任务存在哪里"** — 违反了规则1。应直接去 Reminders 搜索，不要再问。
- **跳过备注流程**：完成提醒时必须 `edit --notes`（有备注时）+ `complete`，不能只 complete 就结束。
- **用 notes 而非 title 存备注**：正确做法是 `edit --notes`，而不是把备注塞进标题。
- **用数字索引操作跨列表任务**：始终用 JSON ID。
