---
category: media
name: douyin-transcription
version: 2.0.0
description: 抖音视频转文字/逐字稿，支持批量断点续传。从抖音视频链接提取音频，用 Whisper 转写，结果先缓存本地再推送到飞书多维表格，中断可自动续传。
trigger: 抖音转文字、抖音逐字稿、抖音视频转写、douyin 字幕、抖音 transcription、抖音批量转写、创哥转写
tags: [douyin, 抖音, transcription, whisper, 视频转文字, 批量]
priority: high
---

# 抖音视频转文字逐字稿（v2 断点续传版）

## 核心机制：转写缓存 + 自动续传

**断点续传流程：**
1. 转写完成 → 先落盘到 `~/douyin_cache/aweme_id/{aweme_id}.txt`
2. 推送飞书 → 成功则删除缓存，失败则保留
3. 下次运行 → 自动扫描缓存目录，未完成的自动重试

**缓存目录：** `~/douyin_cache/aweme_id/`
**临时目录：** `/tmp/douyin_resume3/`

---

**只推缓存、不下载新任务（当用户说"停止下载"时用）：**
```bash
python3 ~/.hermes/scripts/douyin_chuang_push_cache.py
```
脚本扫描 `~/douyin_cache/aweme_id/` 中所有缓存文件，逐一推飞书，成功后删除缓存，失败保留。

**下载失败（rc=0）处理：** 抖音直链约数小时后过期，curl 返回 0 字节文件。rc=0 表示服务器响应成功但内容为空（与 rc=6 网络超时不同）。此时需重新从浏览器抓新直链，不能继续用旧 URL。

**下载失败（rc=6）处理：** 网络层超时，通常是 DNS/连接问题，可重试。

---

## 飞书推送命令（lark-cli）

**写入多维表格：**
```bash
lark-cli base +record-batch-create \
  --base-token NeDBbyQvTa0xdysDCbRcQZ8cnMf \
  --table-id tbllE5S5vOhj5W9x \
  --as user \
  --json '...'
```

### 关键陷阱：`--json @filepath` 必须用相对路径

lark-cli 的 `--json` 支持 `@filepath` 语法读取 JSON 文件，但 **路径必须是相对路径**（相对于当前工作目录），不能用绝对路径。

```bash
# 错误（报错："must be a relative path within the current directory"）
lark-cli base +record-batch-create ... --json '@/tmp/payload.json'

# 正确（相对路径）
echo '{"fields":[...],"rows":[[...]]}' > ./payload.json
lark-cli base +record-batch-create ... --json '@/payload.json'
```

**Python 调用时**：subprocess.run() 在 `~/.hermes/scripts/` 执行，JSON 文件写入 `./feishu_payload_{aweme_id}.json`（相对路径），不要写入 `/tmp/`。用 `--dry-run` 验证命令格式。

---

## 单视频快速转写（备用）

适用场景：快速转写一个视频，不需要批量处理。

### Step 1 — 获取视频直链

用 agent-browser headless 抓 HAR：

```bash
agent-browser open "https://www.douyin.com/video/<VIDEO_ID>"
agent-browser network har start
agent-browser reload
sleep 5
agent-browser eval "(() => { const v = document.querySelector('video'); if(v) v.play(); return 'playing'; })();"
agent-browser network har stop /tmp/douyin_video.har
```

从 HAR 提取音频直链：

```bash
cat /tmp/douyin_video.har | python3 -c "
import json, sys
har = json.load(sys.stdin)
entries = sorted(har.get('log', {}).get('entries', []),
                 key=lambda e: e.get('startedDateTime', ''), reverse=True)
for e in entries:
    url = e.get('request', {}).get('url', '')
    if 'media-audio-und-mp4a' in url and 'douyinvod.com' in url:
        print(url)
        break
"
```

> ⚠️ 抖音直链会过期（约数小时），批量脚本里预存了近期视频的 play_url，新视频需要重新抓包。

### Step 2 — 下载 + 转写

```bash
curl -L -o /tmp/douyin_audio.mp4 "<AUDIO_URL>" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36" \
  -H "Referer: https://www.douyin.com/" \
  -H "Accept-Language: zh-CN,zh;q=0.9" \
  --max-time 300 -s

whisper /tmp/douyin_audio.mp4 \
  --model base \
  --language Chinese \
  --output_dir /tmp \
  --output_format txt
```

### Step 3 — 推送飞书（单条）

```bash
lark-cli base +record-batch-create \
  --base-token NeDBbyQvTa0xdysDCbRcQZ8cnMf \
  --table-id tbllE5S5vOhj5W9x \
  --as user \
  --json '{"fields": ["文章标题", "原文内容", "原文链接", "时长", "点赞数", "来源种类", "博主名称", "发布日期"], "rows": [["标题", "转写内容", "https://www.douyin.com/video/ID", 时长, 点赞数, "抖音", "博主名", UNIX_MS]]}'
```

---

## 备选分支：视频有字幕轨道

有些抖音视频开启了字幕（CC 按钮）。此时无需下载+转写，直接从 DOM 提取：

```bash
agent-browser open "<视频链接>"
agent-browser eval "
(() => {
  const tracks = document.querySelector('video').textTracks;
  if (tracks.length === 0) return 'NO_SUBTITLES';
  let text = '';
  for (let t of tracks) {
    if (t.kind === 'subtitles' || t.kind === 'captions') {
      for (let c of t.cues) text += '[' + c.startTime.toFixed(3) + '] ' + c.text + '\n';
    }
  }
  return text || 'EMPTY';
})();
"
```

返回空或 `NO_SUBTITLES` 则回退到 Whisper 流程。

---

## 常见问题

**Q: 飞书推送失败（rc=0 但 resp=空）？**
A: lark-cli 的 --json 参数格式容易出错。建议检查 lark-cli 版本，用 `lark-cli auth login --domain base` 重新认证。

**Q: 下载失败 rc=6？**
A: 直链过期。抖音视频直链有效期很短，预存 URL 在 1-2 天后可能失效。批量脚本里的 URL 是抓取时刻的，需要更新直链。

**Q: Whisper 超时？**
A: 超时公式：`max(300, min(1200, duration * 2))` 秒。设置足够长的 timeout 即可。

**Q: 转写结果有错别字？**
A: Whisper base 模型中文错误率约 5-10%，财经专业词汇（ETF/FOF/超额收益等）需人工校对。音频质量差时错误率更高。

**Q: 批量任务中断了怎么办？**
A: 直接重跑脚本。v5 脚本会自动扫描 `~/douyin_cache/aweme_id/` 目录，已完成的跳过，未完成（缓存还在）的自动重试推飞书。

**Q: curl 返回 403？**
A: 请求头不完整。必须从 HAR 复制完整的原始 URL（含所有 query params），并带上 Referer 和 User-Agent。

---

## 飞书多维表格信息

- **app_token:** `NeDBbyQvTa0xdysDCbRcQZ8cnMf`
- **文章内容表 table_id:** `tbllE5S5vOhj5W9x`
- **字段:** 文章标题 / 原文内容 / 原文链接 / 时长 / 点赞数 / 来源种类 / 博主名称 / 发布日期
- **认证:** `lark-cli auth login --domain base`（device code 方式）

## 验证步骤

1. ✅ `ls ~/douyin_cache/aweme_id/` 确认缓存目录存在
2. ✅ Whisper 输出包含中文文本
3. ✅ 飞书多维表格出现新记录
4. ✅ 推送消息到达飞书 home channel（批量任务完成后）
