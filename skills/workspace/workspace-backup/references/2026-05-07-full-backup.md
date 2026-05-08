# 备份履历：2026-05-07 全量备份

## 触发

用户要求重新备份，不用分两个包。

## 方案

**单包全量备份**（排除 hermes-agent/，2.5G）：

```bash
# 1. rsync 同步到临时目录
rsync -av --exclude='hermes-agent/' --exclude='bin/' --exclude='cache/' \
  --exclude='image_cache/' --exclude='logs/' --exclude='tmp/' \
  --exclude='weixin/' --exclude='whatsapp/' --exclude='sandboxes/' \
  --exclude='.DS_Store' --exclude='*.swp' --exclude='gateway.lock' \
  --exclude='gateway.pid' --exclude='state.db*' --exclude='kanban.db' \
  --exclude='node_modules/' \
  ~/.hermes/ /tmp/backup_full/

# 2. 打包
tar -czf ~/backup/backup_20260507_full.tar.gz -C /tmp backup_full

# 3. 推送到 GitHub
git clone --depth=1 https://github.com/tevenliang/hermes-backup.git /tmp/hb_repo
cp ~/backup/backup_20260507_full.tar.gz /tmp/hb_repo/
cd /tmp/hb_repo && rm -rf .git && git init && git add backup_xxx.tar.gz && git commit -m "Backup: 2026-05-07 full backup"
git remote add origin https://github.com/tevenliang/hermes-backup.git
git push -u origin main --force
```

## 体积分布

| 目录 | 原始大小 | 备注 |
|------|----------|------|
| hermes-agent/ | 2.5G | 排除（框架代码） |
| sessions/ | 107M | 纳入 |
| skills/ | 23M | 纳入 |
| memories/ | 5.9M | 纳入 |
| memory/ | 2.4M | 纳入 |
| 总计 | ~143M（同步后） | 压缩后 40MB |

结论：排除 hermes-agent 后用户数据约 143M，单包即可，远低于 500M 限制。

## 教训

- **terminal shell 会话损坏**：`git clone` 到 `/tmp/` 时当前 shell 的 cwd 被覆盖，后续所有 `cd ~` 命令都失败。换用 `execute_code` python subprocess 绕过。
- Skill 文档里提到的「每日抖音 cron 任务」早已被用户删除，cron 列表只有 4 个任务（getnote-sync/daily-finance 已暂停，daily-summary/workspace-backup 正常）。
