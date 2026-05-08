# 知识库表字段参考

> 以下为已知字段，实际以 `lark-cli base +table-fields-list` 返回为准。

## App Token & Table ID
- App Token：`VNLrbIYoAausDOs5uovcO7fPn0d`
- Table ID：`tbl2vVHnujNPQczd`

## 常用字段

| 字段含义 | 预期字段名（模糊匹配） | 备注 |
|---------|----------------------|------|
| 企业名称 | `企业名称` | 主键，必须 |
| 新闻链接 | `新闻链接`、`原文链接` | URL 类型，可为空 |
| 文档链接 | `文档链接`、`飞书文档` | 创建后回填 |
| 更新时间 | `更新时间`、`更新时间` | 日期类型，回填当天日期 |

## 回填字段优先级
1. 优先写 `文档链接` / `新闻链接` 字段
2. 其次写 `更新时间` 字段

## record-upsert 示例
```bash
lark-cli base +record-upsert \
  --as bot \
  --base-token VNLrbIYoAausDOs5uovcO7fPn0d \
  --table-id tbl2vVHnujNPQczd \
  --record-id {record_id} \
  --json '{"fld_doc_link": "https://xxx.feishu.cn/docx/xxx", "fld_update_time": "2026-04-30"}'
```

> 字段 ID（fldxxx）以实际返回为准，脚本启动时会先查询字段列表再写入。
