# CHANGELOG - 客户新闻追踪

## v1.0.1 (2026-04-30)
- 修复：config.json App Token/Table ID 更正为实际客户 bitable
- 修复：脚本字段映射从"企业名称"改为"Customer"
- 修复：step1 改用 Customer 字段（index 0）读取企业名称
- 修复：step2 跳过已有链接逻辑，改为全量 Tavily 搜索
- 修复：step4 使用正确的 field ID（fldC80mDeb / fldCeGnPG2）直接回填
- 优化：移除 SKILL.md 中错误的 ~/.workbuddy 路径
- 优化：移除 emoji 输出，文本格式更简洁
- 原因：上线前审查发现配置与实际 bitable 不符
