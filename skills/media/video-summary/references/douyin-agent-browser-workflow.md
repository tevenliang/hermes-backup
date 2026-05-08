# Douyin Content Extraction via agent-browser

## The Right Approach: Chrome CDP (Chrome DevTools Protocol)

`agent-browser` by default launches a **fresh headless browser** — no cookies, no login state. For Douyin, you need to connect to the user's **existing Chrome** which is already logged in.

## Setup: Enable Chrome Remote Debugging

The user must start Chrome with remote debugging enabled:

```bash
# Option A: Terminal command (one-time launch)
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222

# Option B: Add to Chrome's shortcut permanently
# On Mac: Edit ~/Library/Google/Chrome/google-chrome shortcut
# Add flag: --remote-debugging-port=9222
```

**Important**: If Chrome is already running, you need to close it first, then launch with the flag from terminal.

## Connect via CDP

```bash
agent-browser --cdp 9222 open https://www.douyin.com/video/7634760396226336116
agent-browser --cdp 9222 snapshot -i
agent-browser --cdp 9222 screenshot /tmp/douyin-video.png
```

## Workflow for Douyin Video Transcription

1. **User starts Chrome with CDP**: `/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222`
2. **Navigate to video**: User manually opens Douyin video in the CDP Chrome window and logs in if needed
3. **Agent connects**: `agent-browser --cdp 9222 open <douyin-video-url>`
4. **Extract content**:
   - Screenshot: `agent-browser --cdp 9222 screenshot /tmp/douyin.png`
   - Or extract via JavaScript: `agent-browser --cdp 9222 eval "document.body.innerText"`
5. **OCR the screenshot**: `mcp_minimax_understand_image` on the screenshot
6. **Alternative — get video URL via JS**: Douyin's internal API returns video URLs as JSON in the page; can extract via:
   ```bash
   agent-browser --cdp 9222 eval "JSON.stringify(window.__INITIAL_STATE__?.videoResource?.vedioDetails?.videoDetails?.videoDetails?.高清mp4Url)"
   ```

## Simpler Alternative: Just Screenshot + OCR

If the video has visible text/subtitles, the fastest path:
1. User opens video in Chrome (with CDP)
2. `agent-browser --cdp 9222 screenshot /tmp/douyin.png`
3. `mcp_minimax_understand_image` on `/tmp/douyin.png`

This captures whatever is on screen — subtitles, comments, video text.

## CDP Port Check

```bash
# Verify Chrome is listening on 9222
curl -s http://localhost:9222/json/version | jq .browserVersion
```

If nothing returns, Chrome isn't running with `--remote-debugging-port=9222`.

## Note on agent-browser session isolation

agent-browser's `--session` flag creates an isolated profile directory — NOT a connection to an existing Chrome. The `--cdp` flag is the only way to use an already-open Chrome with its cookies. Without `--cdp`, agent-browser is just another headless browser that will fail on Douyin.
