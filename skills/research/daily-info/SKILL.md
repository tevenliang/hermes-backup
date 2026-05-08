category: research
---
name: daily-info
description: 每日资讯动态技能。每天定时收集并整理各类资讯，参考 daily-ai-news-skill 四阶段设计：信息收集 → 分类整理 → 格式化输出。触发词：「每日资讯」「今日资讯」「最新资讯」。
---

# 每日资讯动态 - Skill 设计文档

## 四阶段工作流

```
Phase 1: 信息收集
  ├─ Part 1: 5个精选话题 × (腾讯新闻5条 + 微信公众号3条)
  ├─ Part 2: 腾讯新闻热点榜 Top 10
  └─ Part 3: 华尔街见闻热文 8条
      ↓
Phase 2: 分类整理（5大类别）
  ├─ 🔥 重大事件
  ├─ 🌏 国际时政
  ├─ 🤖 AI科技
  ├─ 💻 科技互联网
  └─ 🏀 文体娱乐
      ↓
Phase 3: 格式化输出
  └─ 每条含：标题 + 摘要 + 链接 + 分类标签
```

## 数据源

### Part 1: 精选话题（5个）
| 话题 | 图标 | 搜索词 |
|------|------|--------|
| AI工具/OpenClaw | 🤖 | OpenClaw 2026 最新更新 |
| 飞书动态 | 📱 | 飞书 2026 最新功能更新 |
| 美以伊/国际局势 | 🌍 | 伊朗 美国 以色列 战争 最新动态 |
| 文班亚纳/体育 | 🏀 | 文班亚纳 NBA 马刺 |
| AI Coding | 💻 | AI Coding 开发工具 2026 |

每话题：
- 腾讯新闻搜索 × 5条
- 微信公众号搜索 × 3条

### Part 2: 腾讯新闻热点榜
- tencent-news-cli hot × 10条

### Part 3: 华尔街见闻热文
- 华尔街见闻 API × 8条

## 分类规则

每条内容自动打分类标签：

| 类别 | 关键词 |
|------|--------|
| 🔥 重大事件 | 战争、地震、灾情、疫情、爆炸、死亡、袭击、突发、黑天鹅 |
| 🌏 国际时政 | 美国、中国、俄罗斯、欧盟、以色列、伊朗、中东、乌克兰、北约、外交 |
| 🤖 AI科技 | AI、ChatGPT、大模型、DeepSeek、OpenAI、Anthropic、Google、Meta、微软、英伟达、芯片 |
| 💻 科技互联网 | 腾讯、阿里、字节、百度、京东、小米、华为、苹果、特斯拉、车企 |
| 🏀 文体娱乐 | NBA、文班、詹姆斯、湖人、勇士、足球、欧冠、电影、明星 |
| 📋 综合 | 无匹配关键词时 |

## 输出格式

每条资讯结构：
```
**标题**
_摘要内容_
🔗 [查看原文](url)
📂 分类标签
```

## 飞书文档发布

脚本运行完成后**必须**执行以下步骤：

1. 用 `lark-cli docs +create --title "每日资讯动态 {日期}" --markdown @./tmp/daily_info.md --as user --folder-token K312fSiL0lApa8dLCARczd1jnUO` 创建飞书文档
2. 获取返回的 `doc_url`
3. **立即调用 `send_message` 推送到用户飞书 DM**（`target=feishu`），内容格式：
   ```
   📰 每日资讯动态 {日期}
   🔗 {doc_url}
   ```
4. 脚本 stdout 末尾也输出同样格式，cron 会自动推送

> **用户铁律**：生成飞书文档后必须推送链接，不能只打印输出。

## 依赖工具

| 工具 | 正确路径 |
|------|---------|
| tencent-news-cli | `/Users/twliang/.tencent-news-cli/bin/tencent-news-cli` |
| search_wechat.js | `/Users/twliang/.hermes/skills/workspace/wechat-article-search/scripts/search_wechat.js` |
| 华尔街见闻 API | 直连 `https://api-one-wscn.awtmt.com/apiv1/content/information-flow` |
