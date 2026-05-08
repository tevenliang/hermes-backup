---
name: apple-notes
description: "Manage Apple Notes via memo CLI: create, search, edit."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [macos]
metadata:
  hermes:
    tags: [Notes, Apple, macOS, note-taking]
    related_skills: [obsidian]
prerequisites:
  commands: [memo]
  verification: |
    memo notes
    # If hangs → System Settings → Privacy & Security → Automation → memo → enable Notes.app
---

# Apple Notes

Use `memo` to manage Apple Notes directly from the terminal. Notes sync across all Apple devices via iCloud.

## Prerequisites

- **macOS** with Notes.app
- Install: `brew tap antoniorodr/memo && brew install antoniorodr/memo/memo`
- **Authorization required** (first run will prompt): System Settings → Privacy & Security → Automation → find `memo` → enable Notes.app
- Note: `memo` will appear to hang/timed-out on first run if authorization not granted. After granting permission in System Settings, re-run.

## When to Use

- User asks to create, view, or search Apple Notes
- Saving information to Notes.app for cross-device access
- Organizing notes into folders
- Exporting notes to Markdown/HTML

## When NOT to Use

- Obsidian vault management → use the `obsidian` skill
- Bear Notes → separate app (not supported here)
- Quick agent-only notes → use the `memory` tool instead

## Quick Reference

### View Notes

```bash
memo notes                        # List all notes
memo notes -f "Folder Name"       # Filter by folder
memo notes --search              # Interactive fuzzy search (prompts for query)
memo notes --search "keyword"    # ⚠️ NOT: -s takes no argument
```

**注意**：`memo notes -s` 不接受搜索词参数，搜索是交互式的。若脚本调用，用 `memo notes | grep "keyword"` 替代。

### Search Notes

**IMPORTANT**: `-s` flag takes NO argument. To search, pipe to grep:
```bash
memo notes | grep "keyword"      # Search notes by keyword
```
If `memo notes` hangs on first run → System Settings → Privacy & Security → Automation → memo → enable Notes.app. After granting permission, re-run.

### Create Notes

```bash
memo notes -a                     # Interactive editor
memo notes -a "Note Title"        # Quick add with title
```

### Edit Notes

```bash
memo notes -e                     # Interactive selection to edit
```

### Delete Notes

```bash
memo notes -d                     # Interactive selection to delete
```

### Move Notes

```bash
memo notes -m                     # Move note to folder (interactive)
```

### Export Notes

```bash
memo notes -ex                    # Export to HTML/Markdown
```

## Limitations

- Cannot edit notes containing images or attachments
- Interactive prompts require terminal access (use pty=true if needed)
- macOS only — requires Apple Notes.app
- **Authorization timeout**: If `memo notes` times out, it means macOS hasn't granted automation access yet. Go to System Settings → Privacy & Security → Automation, find `memo`, and enable Notes.app. Then retry.

## 搜索笔记（重要陷阱）

`-s` 参数不能直接跟搜索词，会报 `unexpected extra argument`。正确方式：

```bash
# 方式1：列出全部，再用 grep 过滤（稳定，推荐）
memo notes | grep "关键词"

# 方式2：-s 单独使用会进入交互式搜索，会卡住，不要用
memo notes -s "关键词"   # ❌ 会报 Error
```

这是 `memo` CLI 的已知行为，不支持管道输入搜索词。

## 与 Get笔记 的区分

两个 skill 都能搜笔记，但数据源不同：
- **Apple Notes**：本地 macOS，云端同步 Apple 设备
- **Get笔记**：biji.com 云端服务，API 驱动

当用户说"找笔记"时，优先询问数据源，或同时搜两个再合并结果。若只搜到一个且用户没指定，默认搜 Apple Notes。

## Rules

1. Prefer Apple Notes when user wants cross-device sync (iPhone/iPad/Mac)
2. Use the `memory` tool for agent-internal notes that don't need to sync
3. Use the `obsidian` skill for Markdown-native knowledge management
