# Image Handling in Feishu

## Correct Approach (2026-05-04)

MiniMax M2.7 is **text-only** — it does NOT support image input natively. The previous assumption that the model could "see images directly" was wrong and caused repeated failures.

### Correct Workflow
1. User shares image in Feishu → downloads to `~/.hermes/image_cache/img_<hash>.jpg`
2. Call `mcp_minimax_understand_image` with the local file path and a prompt
3. Return the description to the user

```python
# Example: describe an image
mcp_minimax_understand_image(
    image_source="/Users/twliang/.hermes/image_cache/img_xxx.jpg",
    prompt="详细描述这张图片的内容"
)
```

### Why `vision_analyze` Doesn't Work
- `vision_analyze` requires `auxiliary.vision` to be configured with a vision-capable model
- `auxiliary.vision` is empty — no vision API key configured
- MiniMax M2.7's native endpoint does not accept image inputs
- Previous attempts to use vision_analyze all failed with errors or timeouts

### Why Native Multimodal Doesn't Work
- MiniMax M2.7's `/v1/chat/completions` endpoint only accepts text with Token Plan API keys
- `GET /v1/models` only lists text models for these keys (MiniMax-M2.7, MiniMax-M2.5, etc.)
- Vision must be accessed via `minimax-coding-plan-mcp` MCP server only

### Technical Notes
- Image files are valid JPEG: `file img_xxx.jpg` returns `JPEG image data, JFIF standard`
- Image dimensions available in file metadata (e.g., 1428x658)
- MiniMax Token Plan key format: `sk-cp-g_...`
- MCP tool naming: `mcp_minimax_understand_image`, `mcp_minimax_web_search`
- MCP config location: `~/.hermes/config.yaml` under `mcp_servers.minimax`

## Related
- See `references/bot-migration.md` for bot replacement notes
