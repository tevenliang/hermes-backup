---
name: wallstreetcn-news
category: research
description: 获取华尔街见闻财经新闻。当用户询问华尔街见闻、wallstreetcn、财经新闻、市场动态、金融资讯、股市行情、热文、头条、搜索文章时使用。使用 web_fetch 直接调用 API 获取最新文章、头条文章、热文和搜索结果。
---

# 华尔街见闻新闻

使用 `terminal` + `curl` 调用华尔街见闻 API（不要用 web_fetch/web_extract，该工具会报 blocked）。

## API 接口

| 类型 | URL | 状态 |
|------|-----|------|
| 最新 | `https://api-one-wscn.awtmt.com/apiv1/content/information-flow?channel=global&accept=article&limit=10` | ✅ 实测可用 |
| 头条 | `https://api-one-wscn.awtmt.com/apiv1/content/carousel/information-flow?channel=global&limit=10` | ✅ 实测可用 |
| 热文 | `https://api-one-wscn.awtmt.com/apiv1/content/articles/hot?period=all` | ✅ 实测可用 |
| 搜索 | `https://api-one-wscn.awtmt.com/apiv1/search/article?query=关键词&limit=10` | ⚠️ 疑似失效，返回空 |

## 调用方式

```bash
curl -s "API_URL" | python3 -c "
import json,sys
data = json.load(sys.stdin)
# 解析逻辑见下方
"
```

## 文章摘要说明

API 返回的摘要字段 `content_short` 通常只有 **50-80 字**，信息量有限。若用户要求更详细的摘要，有两种方案：

### 方案 A：展示更多搜索结果（轻量）
增加 `limit` 参数获取更多条目，让用户自己点击原文链接。

### 方案 B：浏览器自动化抓全文（重量）
wallstreetcn 是 SPA（JavaScript 渲染），直接 curl 无法获取正文。需要用 OpenCLI browser 抓取：

```bash
# 用 opencli 打开文章并提取正文
opencli xurl browse "https://wallstreetcn.com/articles/{id}"
```

**注意**：browser 方案每篇文章约需 3-5 秒，不适合批量处理。默认使用 API 的 `content_short` 即可，如用户明确要求详细摘要再使用方案 B。

## 数据解析

### 最新/头条文章
```json
data.items[].resource = {
  "title": "标题",
  "uri": "链接",
  "content_short": "摘要",
  "display_time": 时间戳,
  "author": {"display_name": "作者名"}
}
```

### 热文
```json
data.day_items[] = {
  "title": "标题",
  "uri": "链接",
  "display_time": 时间戳,
  "pageviews": 浏览量
}
```

## 输出格式

使用 Markdown 格式输出（不使用代码块），保持简洁高效：

### 格式模板

```
---
### 📰 华尔街见闻 · WALLSTREETCN
---

**1.【文章标题】**

内容摘要（前 50 字左右）...

> [阅读全文](https://wallstreetcn.com/articles/...) · 作者：作者名 · 2026-03-27 11:00

---

**2.【文章标题】**

内容摘要（前 50 字左右）...

> [阅读全文](https://wallstreetcn.com/articles/...) · 作者：作者名 · 2026-03-27 10:30

---

> 💡 华尔街见闻 —— 帮助投资者理解世界
```

### 输出要求

1. **品牌标识**：顶部使用 `### 📰 华尔街见闻 · WALLSTREETCN`
2. **分隔线**：使用 `---` 分隔每条新闻
3. **标题格式**：`**序号。【标题】**` 加粗显示
4. **摘要**：单独一段，约 50 字，自动换行
5. **元信息**：使用引用格式 `>`，包含链接、作者、日期，用 `·` 分隔
6. **品牌口号**：底部使用 `> 💡 华尔街见闻 —— 帮助投资者理解世界`
7. **不使用代码块**：确保文本自动换行
