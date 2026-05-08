---
name: daily-summary
description: >
  汇总当日（或指定日期）的 AI 助手对话记录，生成格式化工作日志，
  直接在对话框中输出。

  触发词：每日汇报、汇报一下、昨天聊了什么、昨天干了啥、昨天总结、
         今日汇报、今日总结、每日总结
  参数：可附加日期，如"每日汇报 04-21"，省略则默认当天

  输出：B模式（详细），包含所有会话主题、关键操作、问题描述、状态标注。
version: "1.1.0"
allowed-tools: session_search, read_file, write_file, patch, terminal
---

# 每日汇报 Skill

## 功能概述

1. 通过 `session_search` 搜索指定日期的全部对话记录
2. 按主题分类整理（自动化任务 / 数据查询 / 系统配置 / 飞书操作等）
3. 生成带 emoji 的格式化汇报，**直接在对话框中输出给用户**
4. 不创建飞书文档，不写入多维表格
5. 同时写入 `~/.hermes/memory_daily/{日期}.md` 存档

---

## 搜索方法

**必须用 terminal 直接读 session 文件（不用 session_search）**：

session 文件在 `~/.hermes/sessions/`，有两类：
- `session_YYYYMMDD_HHMMSS_*.json` — weixin/飞书 session（每个对话一个）
- `YYYYMMDD_HHMMSS_*.jsonl` — 原始消息日志（cron session 也用这个格式）

**正确流程**：
1. 用 `ls ~/.hermes/sessions/ | grep "^2026{日期}"` 过滤当天文件（注意格式：`20260505` 对应 `20260505` 前缀）
2. 对每个 `.jsonl` 文件用 Python 解析，提取 user 消息的 timestamp 和 content
3. 排除 `session_cron_*` 文件（那是 cron 自己的执行记录，不是用户对话）
4. cron session 的用户消息在 `session_cron_{job_id}_{date}_{time}.json` 里查找

**禁止用 `session_search`**：它只能取 5 个 session，且日期过滤不可靠。

---

## 存档规则

汇报内容同时写入 `~/.hermes/memory_daily/{日期}.md`，追加到当日文件末尾。

格式：
```
---

## {时间} 每日汇报

[汇报内容]
```

---

## 已知限制

1. cron 触发的日报只能"尽力而为"，无法保证 100% 覆盖全天操作
2. session 文件可能包含工具调用和系统消息，需要过滤掉非 user 角色的消息

---

## 日期参数规则

- 无参数：默认取**今天**（T+0）
- 带日期参数：如"每日汇报 04-21"或"每日汇报 2026-04-21"，取指定日期
- 正则匹配：`(\d{2,4}[-/]\d{2}[-/]\d{2})` 提取目标日期

---

## 输出格式（B模式）

```
📅 {日期} 每日汇报

🤖 AI 助手（Javis）工作日志

📌 自动化任务
  • [{时间}] 主题摘要（来源: weixin/cron）
  ...

🔐 账号管理
  • [{时间}] 操作内容

🤖 系统配置
  • [{时间}] 配置变更

📄 飞书/多维表格操作
  • [{时间}] 操作内容

📊 数据查询
  • [{时间}] 查询内容

📎 待处理事项
  → 问题描述 + 解决方案
```

---

## 分组规则

按 session 的 `source`（weixin/cron）和内容关键词综合判断：
- 包含"自动化、每日、脚本、执行" → 自动化任务
- 包含"飞书、文档、lark、feishu、多维表格、base" → 飞书/多维表格操作
- 包含"股票、财经、基金、数据、行情、查询" → 数据查询
- 包含"配置、setup、安装、skill、模型" → 系统配置
- 其他 → 其他

---

## 存档规则

汇报内容写入 `~/.hermes/memory_daily/{日期}.md`，追加到当日文件末尾。

首次初始化（2026-05-04）：已将 memory 工具完整内容写入 `~/.hermes/memory_daily/2026-05-04.md`。

格式：
```
---

## {时间} 每日汇报

[汇报内容]
```

---

## 参考脚本

`references/parse_sessions.py` — 直接解析当天 session JSONL 文件，返回按时间排序的用户消息。可直接运行 `python3 references/parse_sessions.py [YYYYMMDD]` 验证数据完整性。

## 依赖工具

- `terminal` + Python：读取和解析 session JSONL 文件（见上方参考脚本）
- `write_file`/`patch`：写入当日 memory_daily 文件
