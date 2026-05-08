---
category: productivity
name: image-text-extraction
description: Extract text from images using OCR. Triggered when user asks to "识别图片", "提取图片文字", "OCR", "图片转文字", or sends an image asking for its content.
triggers:
  - "识别图片"
  - "提取图片文字"
  - "图片OCR"
  - "图片转文字"
  - "把图片里的字发给我"
  - "图片里写了什么"
  - any image with request to extract/transcribe text content
version: 1.0.0
related_skills:
  - ocr-and-documents
---

# Image Text Extraction (图片文字识别)

## Primary Tool

**`mcp_minimax_understand_image`** — always try this first. This is a MiniMax vision model that handles Chinese + English mixed content well. It is the correct tool for all regular image files (JPG, PNG, HEIC, BMP, WebP, etc.).

> **When NOT to use this skill:** If the file is a PDF or scanned document, use the **`ocr-and-documents`** skill instead. Do not try to convert images to PDF and then use marker-pdf — it requires ~2.5GB model download and frequently times out on first run.

**What this skill handles well:**
- 手机截图 (phone screenshots)
- 拍摄的文件/书籍照片 (photos of documents/books)
- 表格图片 (images containing tables)
- 带水印的图片 (images with watermarks — content under watermarks may be partially occluded)

**Known limitations:**
- Text directly covered by watermarks cannot be recovered (the actual pixel data is lost)
- Very small text or low-resolution images may have reduced accuracy

## Workflow

### Step 1: Use mcp_minimax_understand_image with comprehensive prompt

Call with a very detailed prompt that explicitly requests complete, exhaustive text extraction:

```
请极其仔细地识别这张图片中的每一个文字。这张图片可能包含：
1. 表格内容
2. 标题和副标题
3. 注释和说明文字
4. 底部或角落的小字
5. 任何符号或数字
请逐行逐字识别所有文字，不要遗漏任何内容。
```

The key phrases that improve completeness:
- "极其仔细" (extremely carefully)
- "每一个文字" (every single character)
- "不要遗漏" (don't miss anything)
- List specific content types that might be present (tables, captions, footnotes, etc.)

### Step 2: If result seems incomplete

The user will often say "内容发少了" or "并没有全部识别". In that case:
- Re-call with an even more explicit prompt asking about the missing areas
- Ask the user to point to the specific region they're referring to

### Step 3: Format the output

Present extracted text in a clean, readable format appropriate to the content type:
- Tables → markdown table format
- Plain text → clean paragraph
- Mixed content → structured sections

## Pitfalls

1. **Don't tool-jump**: Don't try multiple OCR tools in sequence hoping one works. Use `mcp_minimax_understand_image` and iterate on the prompt if needed.
2. **Don't assume the first result is complete**: Chinese OCR models may truncate or skip small text. The user telling you it's incomplete IS the iteration signal — re-call with a more detailed prompt.
3. **Handle edge cases**: Some images have watermarks, phone numbers, or partial text. If user says content is missing, ask for clarification on which part before re-calling.
4. **Don't explain what you're about to do**: User doesn't need to know "I'm going to use the vision model to extract text". Just do it and deliver the text.
5. **Never convert image → PDF → marker-pdf for OCR**: This path requires ~3-5GB download (PyTorch + models) and frequently times out. It is designed for scanned PDF documents, not JPG/PNG phone screenshots. Use `mcp_minimax_understand_image` directly — it handles images natively and is faster.
6. **Watermarks are irrecoverable**: Text directly covered by a watermark (logo, username, phone number) cannot be extracted — the underlying pixel data is lost. In these cases, acknowledge what you cannot see rather than guessing. The model may "hallucinate" plausible but incorrect text (e.g., a partially-occluded number like "617万" being reported as "611万" or "612万"). When uncertain, explicitly state the limitation rather than filling in a guess.

小红书帖子抓取（xsec_token workaround）已迁移至 `opencli-tool` skill。

## 大文件安装警告（重要）

**在安装任何需要下载 GB 级别文件的工具之前，必须先征得用户同意。** 包括但不限于：
- marker-pdf（~3-5GB，PyTorch + 模型文件）
- 大型 ML 模型
- 任何 pip install / npm install / brew install 会触发大量下载的操作

执行流程：
1. 估算磁盘占用和下载时间
2. 告知用户预计大小和耗时
3. 获得同意后再安装
4. 安装期间如超时应主动停止，不要无限等待

## Verification

After extraction, scan the output for:
- Are all table rows/columns present?
- Are numbers and symbols complete?
- Is the bottom footnote/data source included?
- Any truncated entries?

If anything looks obviously cut off (e.g., a number ending in "6" or "1."), re-call with prompt noting the specific area.
