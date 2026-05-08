# CHANGELOG - getnote-sync

## v1.2 (2026-04-28)
- 修复：bitable 写入改用 lark-cli generic API（`lark-cli api POST .../records/batch_create`），原 `openclaw tools call feishu_bitable_create_record` 命令不存在导致所有写入均失败
- 修复：getnote-sync 历史上所有笔记均未成功写入飞书多维表格（从 04-10 至今），本次修复后重新同步

## v1.1 (2026-04-28)
- 修改：修复 processed 标记时机 bug——ID 原本在文档创建前就标记为已处理，导致创建失败时笔记永久丢失重试机会；现改为文档创建成功后才标记
- 修改：bitable 写入改为非阻塞（失败只打印警告，不阻止主流程，不影响主文档同步）
- 原因：12:40 的两条笔记（1908416392/1908416326）之前某次同步时标记了 processed 但文档实际未创建成功，之后每次同步都跳过，直到今天才发现

## v1.0 (2026-04-10)
- 初始版本
