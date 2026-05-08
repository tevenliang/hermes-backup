# Douyin 视频转录技术参考

## 已知方法及状态

| 方法 | 状态 | 说明 |
|------|------|------|
| `yt-dlp --cookies <file>` | ❌ 失败 | Douyin 检测浏览器环境，Cookie 导出后仍被拒绝 |
| EditThisCookie JSON → Netscape 转换 | ❌ 失败 | 转换本身成功，但 yt-dlp 仍报 "Fresh cookies needed" |
| `agent-browser` 控制 Chrome | ✅ 可行 | Chrome 已有登录态，不需要手动导出 Cookie |
| Whisper 本地离线转录 | ✅ 可行 | yt-dlp 下载视频（无需 Cookie）+ Whisper 转录，不依赖登录态 |
| `video-summary` skill | ⚠️ 受限 | 同样需要 `--cookies`，受相同限制 |

## 推荐方案

**方案 A（首选）：agent-browser 控制 Chrome**

Chrome 本身已有登录态，直接用 `agent-browser` 操作已打开的 Douyin 页面，最可靠。

**方案 B（备选）：yt-dlp 下载 + Whisper 转录**

```bash
# 1. 用 yt-dlp 下载（不需要 Cookie，公开视频）
yt-dlp "https://v.douyin.com/ZdbZCAHFvfI/" -o /tmp/douyin_video.mp4

# 2. Whisper 转录
whisper /tmp/douyin_video.mp4 --model medium --language Chinese
```

## Douyin 反爬机制

Douyin 使用以下机制检测自动化工具：
1. Browser fingerprint（Canvas、WebGL、字体）
2. Cookie 环境完整性（部分 cookie 需 httpOnly + secure）
3. TLS fingerprint（JA3 指纹）
4. JavaScript 挑战（CIKM/Bot verification）

导出到文件的 Cookie 缺少浏览器运行时环境信息，所以被拒绝。

## 关键 Cookie 字段

至少需要以下 cookie 才可能被 yt-dlp 接受：
- `sessionid` / `sid_tt` — 会话 token（httpOnly）
- `ttwid` — 设备 token（httpOnly + secure）
- `sid_guard` — 会话保护

但即使有这些，TLS/JA3 指纹不匹配仍会导致失败。

## 当前待处理任务

用户有一支抖音视频待转录：`https://v.douyin.com/ZdbZCAHFvfI/`
用户选择了方案 A（agent-browser），等待执行。
