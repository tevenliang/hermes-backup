# 2026-05-06 hermes-backup session record

## 背景

用户重启电脑后，要求重新执行之前网络失败中断的 GitHub 上传任务：将 `~/.hermes/` 备份到 `https://github.com/tevenliang/hermes-backup`。

## 关键发现

### 1. rsync 排除不完全的问题

rsync 的 `--exclude='*.pyc'` 和 `--exclude='__pycache__/'` 对已经存在的目录树效果有限——文件仍可能被带入。

**Session 中的教训**：rsync 完成后，`/tmp/hermes-backup/` 里仍有 `.hermes_history`、`.update_check`、`auth.lock`、`cron/` 等需要手动清理。

**解决**：rsync 后立即进入备份目录执行清理命令（见 SKILL.md Step 4）。

### 2. `.gitignore` 阻断 `git add` 的陷阱

这是本次最关键的 pitfall：

```
$ git add memory_daily/
The following paths are ignored by one of your .gitignore files:
hint: Use -f if you really want to add them.
```

原因：克隆下来的目标仓库里已有 `.gitignore`，其中包含 `memory_daily/` 的排除规则。

**解决**：
1. 修改备份目录的 `.gitignore`，将 `memory_daily/` 行改为注释：
   ```
   # memory_daily/ - INCLUDED in backup (contains important daily memories)
   ```
2. 然后 `git add memory_daily/`

### 3. 排除模式汇总（实际使用的）

本次备份最终排除了：
- `.hermes_history/`、`.update_check`、`auth.lock`
- `cron/`（任务配置，未用户确认是否保留）
- 所有 `*.json`（但 scripts 目录下的非临时脚本保留）
- 所有 `scripts/` 下的临时文件：`meta_*.txt`、`note_*.txt`、`temp_*.txt`、`*_state.json`
- 大量辅助脚本（check_*.sh、cleanup_*.py、delete_*.py 等）

### 4. 历史脚本的处理

用户确认：**历史脚本也上传**（`daily_finance_v4_DEPRECATED.py`、`douyin_daily_v0.py` 等废弃版本也保留）。

用户确认：**临时文件排除**（`meta_*.txt` 等）。

## 最终上传内容

```
~/.hermes/
├── skills/          ✓ (451 files)
├── scripts/         ✓ (含历史版本，排除临时文件)
├── memories/        ✓
├── memory_daily/    ✓ (2026-05-04.md, 2026-05-05.md)
├── miaoxiang/       ✓ (mx_finance_search 缓存)
├── bookmark-sync/   ✓
├── SOUL.md          ✓
├── MEMORY.md        ✓
├── USER.md          ✓
├── HEARTBEAT.md     ✓
├── IDENTITY.md      ✓
├── DREAMS.md        ✓
├── TOOLS.md         ✓
├── AGENTS.md        ✓
├── config.yaml      ✓
└── README.md        ✓
```

## GitHub 认证状态

`gh auth status` 显示已用 `tevenliang` 账号登录，token 存在 keyring，`git push` 无需再次输入密码（警告 `git: 'credential-gh' is not a git command` 可忽略，push 仍成功）。

## 教训

1. **每次 rsync 后立即检查实际同步了哪些内容**，不要假设排除模式完全生效
2. **目标仓库的 `.gitignore` 会阻断 `git add`**，对重要目录要先检查并修改
3. **用户说"直接上传"和"排除敏感文件"时**，先确认排除范围再执行
