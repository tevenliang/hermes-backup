---
category: media
name: daily-douyin
description: |
  每日抖音博主动态同步任务。每天 18:30 自动执行（cron），扫描「抖音常看」(VIP) 和「抖音」(普通) 
  两个 GetNotes 知识库，抓取昨天+今天的新帖子，写入飞书文档并推送结果。
  
  用户手动触发时说：「每日抖音」「每日抖音动态」「抖音日报」
---

# 每日抖音 Skill

**状态：已废弃（cron 已删除）。** 保留此文档作为历史参考，不再用于自动化任务。

## 触发方式

- **手动触发**：用户说「每日抖音」「每日抖音动态」「抖音日报」
- **自动执行**：每天 18:30 via cron（job: 每日抖音）

---

## 执行方式

### 自动化模式（cron 调用）

直接运行脚本，不分析不搜索不要解释：

```bash
python3 /Users/twliang/.hermes/skills/media/daily-douyin/scripts/douyin_daily.py
```

脚本会：
1. 扫描「抖音常看」(VIP) + 「抖音」(普通) 两个 GetNotes 知识库
2. 抓取昨天 + 今天的新帖子
3. 生成飞书文档（标题格式：每日抖音动态-YYYYMMDD-HHMM）
4. 写入快捷方式到「400 贾维斯」文件夹
5. 输出完成信息和文档链接

### 手动模式（对话触发）

当用户在对话框说「每日抖音」时：
- 直接运行 `python3 /Users/twliang/.hermes/skills/media/daily-douyin/scripts/douyin_daily.py --direct`
- 内容直接输出到对话框（不去重、不写飞书文档、不更新 state）
- 时间范围：昨天 + 今天

---

## 目标资产（MacBook 本机路径）

| 资产 | 路径 |
|------|------|
| 主脚本 | `/Users/twliang/.hermes/skills/workspace/daily-douyin/scripts/douyin_daily.py` |
| 状态文件 | `/Users/twliang/.hermes/scripts/douyin_state.json` |
| 内容缓存 | `/Users/twliang/.hermes/scripts/douyin_content_cache.json` |

## 已知问题（需修复）

**脚本 Bug：`FileNotFoundError: douyin_content_cache.json`**

脚本 `douyin_daily.py` 第 57 行硬编码了旧 VM 缓存路径：
```python
# 错误（旧路径）
with open("/Users/twliang/.openclaw/scripts/douyin_content_cache.json", "w") as f:
```
修复：替换为 `~/.hermes/scripts/douyin_content_cache.json`（即 `/Users/twliang/.hermes/scripts/douyin_content_cache.json`）。

同时脚本第 477 行附近调用的 `CACHE_FILE` 也需要更新为 `~/.hermes/scripts/douyin_content_cache.json`。

**执行前必须先修复此路径问题，否则脚本会在首次写入缓存时 crash。**

## 手动触发方式

用户说「每日抖音」时：
```bash
python3 /Users/twliang/.hermes/skills/media/daily-douyin/scripts/douyin_daily.py --direct
```

自动化模式（修复路径后）：
```bash
python3 /Users/twliang/.hermes/skills/media/daily-douyin/scripts/douyin_daily.py
```

---

## 知识库配置

| 知识库 | topic_id | 类型 |
|--------|----------|------|
| 抖音常看 | 40DwN71Y | VIP |
| 抖音 | EJleDrPn | 普通 |

---

## 输出格式

### 自动化模式（飞书文档）

标题：`每日抖音动态-20260427-1830`

内容结构：
- ⭐️ 抖音常看（H1）
  - 【博主名】（H2）
    - 帖子标题（H3）
    - 帖子摘要正文
    - 🔗 原文链接
- 📌 抖音（H1）
  - 同上结构

### 手动模式（对话框）

直接 cat 输出，完整内容不截断。

---

## 注意

- cron 模式使用 state.json 去重，避免重复写入
- 手动模式不去重，显示昨天+今天所有帖子
- 脚本内部已有缓存机制（30分钟TTL），不要重复拉 API
