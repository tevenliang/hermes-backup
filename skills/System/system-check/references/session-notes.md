# Skills 清理会话笔记

## 2026-05-05 技能目录重组

### 执行的操作
- 删除 mlops/、dogfood/、devops/、creative/（保留 humanizer → productivity）
- 移动 yuanbao → research → 已删除
- 移动 feishu-lark (lark-mcp/) → productivity/
- 移动 yuanbao/tavily/opencli → research/
- 确认 system-check cron 已绑定（job_id 03972f608185）

### 关键教训
**跑题风险**：用户第一句话问 CPU/内存，我直接进了 MLOps 清理，完全忽略。系统类查询优先级高于维护类任务。

**Skills 移动检查三步法**：
1. skill_view 确认能找到
2. 检查脚本路径（SKILL.md + 内部脚本的硬编码路径）
3. hermes skills list 确认 enabled 状态

**直接回答原则**：
- 用户问"是不是现在才改的" → 直接说"不是，上次 session 已改"
- 用户问"删掉没影响吧" → 直接说"没影响"或"有影响，因为..."
- 不要用解释替代回答

### 系统信息（待补充）
- CPU/内存：需要 `vm_stat` + `pagesize` 查（之前脚本用 `free -h` 不适用 macOS）
