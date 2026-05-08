---
name: douyin-blog-crawler
description: 抖音博主视频爬取 + Whisper转写 + 飞书多维表格写入。触发词：抖音博主爬取、抖音转写任务、爬取博主视频
category: media
version: 1.4.0
---

# 抖音博主爬取转写技能

## 触发条件
用户说"抖音博主爬取"、"抖音转写任务"、"爬取博主视频"时激活。

## 前置条件
- opencli 已安装且 Browser Bridge 已连接（`opencli douyin user-videos` 可用）
- whisper 已安装（`whisper --version` 正常）
- ffmpeg 已安装（`ffmpeg -version` 正常）
- lark-cli 已认证（`lark-cli auth login --domain base` 完成）
- 目标博主抖音主页链接（用于提取 sec_uid）

## 飞书配置（固定值）

**文章内容表** `tbllE5S5vOhj5W9x` 字段映射：

| 字段ID | 字段名 | 说明 |
|--------|--------|------|
| fld1E5qHyW | 文章标题 | 视频标题 |
| fldAiqKG1f | 原文内容 | Whisper转写文本 |
| fldtISSN8i | 原文链接 | `https://www.douyin.com/video/{aweme_id}` |
| fldgnlhG87 | 时长 | 视频时长（秒），数字类型 |
| fldXoQyMmf | 点赞数 | 视频点赞数，数字类型 |
| fldj8CuzKz | 来源种类 | 自动填"抖音"（单选） |
| fldHumOH31 | 发布日期 | 自动填当天日期 |
| fldDessm8s | 博主名称 | 从博主链接表读取 |
| flddJq1h76 | 状态 | 默认留空 |
| fldmAvOzpL | AI标签 | 默认留空 |

**博主链接表** `tbl9cnCB9Hnjxuzb`：记录博主名称和 sec_uid，爬取前从这里读博主名。

## 执行步骤

### Step 0: 检查已有记录（断点续传/复用场景）

**每次执行前必须检查飞书表格中已有 aweme_id，避免重复转写。**

```python
# 推荐：用 Python 获取已有 aweme_id 列表
import subprocess, json

result = subprocess.run(
    'lark-cli base +record-list --base-token NeDBbyQvTa0xdysDCbRcQZ8cnMf '
    '--table-id tbllE5S5vOhj5W9x --as user 2>/dev/null',
    shell=True, capture_output=True, text=True
)
data = json.loads(result.stdout)
existing_ids = set()
for row in data["data"]["data"]:
    url = row[10] if len(row) > 10 else None  # 原文链接字段
    if url:
        existing_ids.add(url.split("/")[-1])
print(f"已有 {len(existing_ids)} 条记录")
```

**判断跳过**：获取视频列表后，`aweme_id` 在 existing_ids 中的直接跳过（见完整 Python 脚本 `references/douyin_resume_logic.md`）。

### Step 1: 从飞书读取博主名称

```bash
lark-cli base +record-list \
  --base-token NeDBbyQvTa0xdysDCbRcQZ8cnMf \
  --table-id tbl9cnCB9Hnjxuzb \
  --as user
```

从返回中找到对应博主的"博主"字段值（注意：字段名是"博主"，不是"博主名称"），备用。

**⚠️ 博主名称不能为空**：如果博主链接表里该博主的"博主"字段为空，必须从视频标题/搜索引擎/浏览器手动补充，否则 batch-create 写入的博主名称字段为空字符串。

### Step 2: 获取博主视频列表

```bash
opencli douyin user-videos "<sec_uid>" --limit 10 --format json
```

sec_uid 从博主抖音主页 URL 末尾提取（URL 本身就是 sec_uid）。

返回字段：aweme_id, title, duration, digg_count, play_url, top_comments

**⚠️ 返回后立即验证视频数量**：
```bash
video_count=$(echo "$videos_json" | jq 'length')
echo "获取到 $video_count 个视频"
if [ "$video_count" -lt 5 ]; then
  echo "警告：视频数异常（<$threshold），sec_uid 可能已失效"
  # 立即停止，告知用户更新 sec_uid
fi
```

**失效症状**：返回 1 个视频（通常是该博主最新那个），而不是 10 个。已失效的 sec_uid 无法修复，必须从抖音APP重新获取。

### Step 3: 下载视频（并行）

用 curl 下载所有视频的 mp4 文件到 `/tmp/douyin_{aweme_id}.mp4`：

```bash
curl -L -o /tmp/douyin_{aweme_id}.mp4 "<play_url>" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36" \
  -H "Referer: https://www.douyin.com/" \
  -H "Accept-Language: zh-CN,zh;q=0.9" \
  --max-time 120 -s
```

**注意**：play_url 有时效性，尽快完成下载。

### Step 4: 提取音频

```bash
ffmpeg -i /tmp/douyin_{aweme_id}.mp4 -vn -acodec libmp3lame -q:a 2 /tmp/douyin_{aweme_id}.mp3 -y
```

### Step 5: Whisper 转写（顺序执行，禁止并行）

```bash
# MacBook CPU 用 base 模型，比 small 快 3-4 倍，长视频不易超时
# 超时阈值：duration <= 300s → 600s；duration > 500s → 900-1200s
whisper /tmp/douyin_{aweme_id}.mp3 --model base --language Chinese --output_dir /tmp --output_format txt
```

**MacBook CPU 优先用 `--model base`**：small 模型在 700s+ 视频上 CPU 转写需要 900s+，容易超时；base 模型约快 3 倍（3-5 分钟 vs 15+ 分钟），更稳定。

**Whisper 超时阈值**：
| 视频时长 | 推荐超时 |
|---------|---------|
| ≤300s | 600s |
| 301-500s | 900s |
| >500s | 1200s（用 base 模型） |

**关键**：Whisper CPU 推理极其占用资源，必须顺序执行。10个视频约需 20-25 分钟。并行会导致所有进程同时争抢 CPU，反而更慢。

### Step 6: 批量写入飞书（一次性完成所有字段）

使用 `+record-batch-create` 一次性写入所有字段（文章标题、原文内容、原文链接、时长、点赞数、来源种类、博主名称），无需分两步。

```bash
lark-cli base +record-batch-create \
  --base-token NeDBbyQvTa0xdysDCbRcQZ8cnMf \
  --table-id tbllE5S5vOhj5W9x \
  --as user \
  --json '{
    "fields": ["文章标题", "原文内容", "原文链接", "时长", "点赞数", "来源种类", "博主名称", "发布日期"],
    "rows": [
      ["<标题1>", "<转写文本1>", "https://www.douyin.com/video/<aweme_id_1>", <时长>, <点赞数>, "抖音", "<博主名称>", <时间戳毫秒>],
      ["<标题2>", "<转写文本2>", "https://www.douyin.com/video/<aweme_id_2>", <时长>, <点赞数>, "抖音", "<博主名称>", <时间戳毫秒>]
    ]
  }'
```

**⚠️ 常用错误：`+record-create` 不存在，会导致静默失败（无报错但数据写不进去）。

返回 `{ "ok": true, "data": { "record_id_list": [...] } }` 表示成功。

**⚠️ 日期格式**：`--json` 中 `发布日期` 必须是毫秒时间戳（Unix epoch × 1000），如 `1745404800000`。飞书会自动转换为 `yyyy-MM-dd` 格式显示。若时间戳为 0，飞书会显示 `1970-01-01`（表示未知日期，需后续手动修正）。

**⚠️ 微博/长视频注意**：某些视频（如图片轮播类）时长为 0，音频提取无意义，跳过即可。但仍可将标题和 0 时长写入飞书。

**无需二次更新**：batch-create 已包含所有必要字段，`+record-upsert` 仅在需要单独修改某条记录时使用。

## 完整流程脚本（推荐 Python）

**使用 Python，不使用 Shell**。Shell 中 `while read` + pipe 的子进程变量不传递，用 Python 实现更可靠。

**脚本选择**：
- `~/.hermes/scripts/douyin_chuang_v5.py` — **当前主力脚本**，断点续传，缓存优先，支持推送失败自动重试
- `~/.hermes/scripts/douyin_chuang_push_cache.py` — 仅推送缓存（不下载），用于"停止下载，只完成缓存"场景

**⚠️ 脚本中的 lark-cli 命令已统一用 `+record-batch-create`，无需修改。**

```bash
# 断点续传（自动跳过已有记录）
python3 ~/.hermes/scripts/douyin_resume_v2.py 2>&1 | tee /tmp/douyin_resume_v2.log
```

## 手动单博主操作

如需单独处理某个博主，使用 `douyin_chuang_v4.py` 作为模板，修改顶部的 `VIDEOS` 列表（从 `opencli douyin user-videos` 的 fresh 输出获取最新 play_url，立即处理）。

## sec_uid 失效检测与恢复（关键）

**问题**：存储在飞书博主链接表中的 sec_uid 会逐渐失效。失效后 `opencli douyin user-videos` 只返回 1 个视频（通常是最新那个），而不是预期的 10 个。

**检测**：每次获取视频列表后，立即检查返回数量：

```bash
video_count=$(echo "$videos_json" | jq 'length')
if [ "$video_count" -lt 5 ]; then
  echo "警告：只获取到 $video_count 个视频，sec_uid 可能已失效"
fi
```

**症状**：
- 返回视频数 < 5
- 返回的标题看起来是旧内容（日期偏旧）
- 视频 aweme_id 与飞书里已有的重复

**sec_uid 恢复流程（按优先级）**：

### 优先级1：v.douyin.com 短链直接提取（最简）

如果用户能提供博主的抖音分享短链接（格式：`https://v.douyin.com/xxx/`），直接用浏览器打开，URL 会重定向到 `https://www.douyin.com/user/MS4wLjABAAAA...`，**sec_uid 就是 URL 末尾的部分**。

```
browser_navigate("https://v.douyin.com/tz4XxCK6AEg/")
# 观察最终 URL: https://www.douyin.com/user/MS4wLjABAAAAX1iRjBCVyMg...
# 提取 URL 末尾的 MS4wLjABAAAA... 即为 sec_uid
```

这是**最可靠**的方法，绕过了抖音所有 JS 混淆和验证码。优先让用户提供 v.douyin.com 短链。

### 优先级2：浏览器访问主页 URL（次选）

如果已知博主主页的长 URL（如 `https://www.douyin.com/user/MS4wLjABAAAA...`），直接访问即可从 URL 中提取 sec_uid。

### 优先级3：RENDER_DATA 提取（验证码拦截时）

```javascript
// 在视频页或主页执行
(() => {
  try {
    const el = document.querySelector('script[id="RENDER_DATA"]');
    const raw = decodeURIComponent(el.textContent);
    const data = JSON.parse(raw);
    // 遍历所有可能的 sec_uid 路径
    const str = JSON.stringify(data);
    const idx = str.indexOf('sec_uid');
    if (idx > 0) return str.slice(Math.max(0, idx-20), idx+80);
    // 备用：user_unique_id（部分情况可替代 sec_uid）
    return 'sec_uid not found, user_unique_id: ' + (data.app?.odin?.user_unique_id || '?');
  } catch(e) {
    return 'error: ' + e.message;
  }
})()
```

⚠️ **抖音有验证码拦截**：视频页和个人主页经常会弹出滑动验证码，浏览器提取会失败。若 `sec_uid not found` 且 browser console 无输出，说明被验证码拦截。此时回退到优先级1（让用户提供短链）。

### 优先级4：搜索引擎找视频页（次选）

当浏览器被验证码拦截时，用搜索引擎找到博主任意一个视频链接：

```bash
# 搜索格式
web_search "「博主名」 site:douyin.com OR 「博主名」 抖音号"

# 找到视频链接后
browser_navigate "<视频链接>"

# 从视频页提取博主名和 sec_uid（见优先级1的JS）
```

⚠️ **抖音视频页的 RENDER_DATA 中 sec_uid 可能不在视频节点**，而是嵌套在作者节点中。如果 `sec_uid not found`，尝试搜索 `user_unique_id` 或博主名作为次优方案。

### 优先级5：搜索引擎直接搜索 sec_uid

```bash
web_search "「博主名」 抖音 sec_uid OR uid OR douyin.com/user"
```

适用于博主已被其他网站收录 sec_uid 的情况（如知乎、CSDN等站外引用）。

### 优先级6：抖音APP手动获取（兜底）

1. 打开抖音APP → 博主主页 → 分享 → 找「复制sec_uid」
2. 如果没有这个选项，选「复制链接」，把链接发给 Steven，让他从链接中提取 sec_uid（URL 末尾或 query string 里）
3. 更新到飞书博主链接表

## 字段名称对照（重要）

飞书多维表格内部字段名与显示名不同，batch-create 和 filter 必须用显示名：

| 表名 | 字段显示名 | 说明 |
|------|-----------|------|
| 博主链接表 tbl9cnCB9Hnjxuzb | 博主 | 博主姓名，用于读取 |
| 文章内容表 tbllE5S5vOhj5W9x | 文章标题 | 视频标题 |
| 文章内容表 tbllE5S5vOhj5W9x | 博主名称 | **注意：这是文章表的博主名字段，非"博主"** |
| 文章内容表 tbllE5S5vOhj5W9x | 来源种类 | 固定值"抖音" |

**常见错误**：把"博主"（博主链接表字段）当作"博主名称"（文章内容表字段）使用，或在 filter 条件中用内部字段 ID 而非显示名。

**⚠️ sec_uid 获取后必须同步两处**：
1. 写入飞书博主链接表（`tbl9cnCB9Hnjxuzb`），字段：`序号`、`sec_uid`、`博主`、`主页链接`
2. 更新记忆：`memory --action replace` 更新 MEMORY.md 中的「抖音sec_uid」列表（格式：`博主名: sec_uid`）

## 关键陷阱：Douyin play_url 会过期

**play_url 有时效性，约 5 分钟内过期。** 这是本任务最常见的失败原因。

**错误模式（URL 分批获取后再下载）**：
1. `opencli douyin user-videos` 获取 10 个视频的 URL → 存入列表
2. 遍历列表依次下载 → **后半部分 URL 已过期，返回 403**

**正确模式（逐个获取-下载-转写，不能批量）**：
1. 获取视频列表（aweme_id, title, duration, digg_count, **play_url）
2. 立即下载该视频（不要等，不要批量获取 URL 后再处理）
3. 立即提取音频 + Whisper 转写
4. 立即写入飞书
5. 清理临时文件，再处理下一个

```python
# 正确做法：获取 → 下载 → 转写 → 写入，闭环处理
for v in videos:
    download_and_transcribe(v)   # play_url 当场用完
    write_to_feishu(v)
    cleanup()
```

**下载卡住的识别与处理**：
- `curl` 下载时若无进度但进程存在，可能是 URL 已失效（返回 403 但 curl 仍等待）
- 检查：`ls -la /tmp/douyin_*.mp4` 看文件大小，0 字节或文件不增长说明下载失败
- 处理：`ps aux | grep curl` 找到进程 PID → `kill <PID>` → 重新获取视频列表（fresh URL）

**Whisper 超时阈值**：
- ≤300 秒视频：600s 超时足够
- >500 秒视频（尤其是 700s+）：设 900s 超时，避免像 915s 视频那样被截断

## 已知限制
- Whisper 无 GPU 加速时，MacBook CPU 转写 10 个视频（约 550 秒总时长）约需 20-25 分钟（用 base 模型约 15 分钟）
- play_url **会过期**（约 5 分钟），必须获取后立即下载，不能等所有 URL 都拿到后再批量处理
- **⚠️ 用 small 模型时，700s+ 视频 CPU 转写会超时（900s 不够）。务必用 base 模型并设 1200s 超时**
- 转写语言硬编码为中文（Chinese），英文内容转写效果会下降
- 评论数字段 opencli 当前版本不返回，暂不支持
- 某些老视频 duration=0（图片轮播类），音频提取无意义，跳过即可
- **长任务易被中断**：每日汇报 cron 在 23:00 执行，若转写任务在 22:00 后启动很可能被截断。务必在 22:00 前启动，或先检查是否有长任务在进行中

## 任务恢复指南

**识别中断**：如果飞书表格里某博主只有部分视频（<10条）且缺少"博主名称"字段，说明上次执行被中断。

**恢复步骤（推荐直接用 Python 脚本）**：

```bash
# 自动完成：检查已有记录 → 遍历全部博主 → 跳过已有 → 爬取缺失 → 写入飞书
python3 ~/.hermes/scripts/douyin_resume.py
```

脚本位于 `~/.hermes/scripts/douyin_resume_v2.py`，同时更新 MEMORY.md 中的博主完成状态。

## 验证步骤
1. 确认 `/tmp/douyin_{aweme_id}.txt` 文件存在且有内容
2. 飞书表格查询 record_id，确认以下字段均已写入：
   - [x] 文章标题
   - [x] 原文内容
   - [x] 原文链接
   - [x] 时长（秒）
   - [x] 点赞数
   - [x] 来源种类（= 抖音）
   - [x] 发布日期
   - [x] 博主名称
