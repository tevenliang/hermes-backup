Workspace: ~/.hermes/（MacBook本机运行，2026-05-04起从VM迁移）
§
生成飞书文档后，必须主动推送链接给用户（send_message 到 feishu），不能只打印输出。
§
Steven 定期清理 skills 目录。偏好简洁直接的回复，不喜欢冗长铺垫。
重要经验：skill 目录迁移后，cron job 的 script 路径不会自动同步，导致三次修复 system-check cron（教训：skill 绑定 cron 后，任何目录迁移必须同步检查 cron prompt 路径）。
他用 MiniMax 云端 API，不涉及本地模型训练/部署/推理。工作流：信息搜索 + 飞书文档 + 任务管理。
清理时默认"没用就删"，但会先看用途再决定。
§
Steven 偏好直接、简洁的回复，不喜欢冗长的铺垫或装饰性语言。对 skill 的建议：若 skill 对他当前工作流无直接价值（如 ontology），即使技术上"正确"也不接受"迁移数据"或"建立双系统"的方案。
§
用户格式偏好：全面检测输出必须直接以纯文本（非代码块）输出在对话框里，不做 summary 不压缩。Skill 里已更新，memory 不记这条。
§
Steven 偏好直接简洁的回复，不需要冗长铺垫。
Steven 的工作流：飞书多维表格管客户/联系人，任务管理软件管项目任务，不需要 ontology。
Steven 正在做 skills 目录大清理（2026-05-05），workspace 从 29 个缩到约 12 个，删掉了 MLOps、creative、software-development、devops、data-science 等整目录。
Skills 分类偏好：productivity / finance / research / News / media / social-media / workspace / System / github 等。
Steven 要求删除任何确认用不上的 skills（财经分析/本地模型/创意工具/学术类）。
Skills 目录迁移后必须同步更新：① SKILL.md 内部路径 ② 所有引用该脚本的 cron job prompts。system-check cron job 路径已错 3 次，每次都是 skill 迁移后 prompt 没跟着更新。
遇到问题时先查官方文档再行动（MiniMax / Hermes Agent / OpenClaw）。
账号密码表 app_token OvQ2bpM6gaez1ksDTYwclTPjnib, table tblvdLBUJJbOouUy
§
Steven 对成本敏感。使用任何付费工具/Skill 前，必须先告知费用情况，不能等试完才说要钱。xurl 这件事留下了教训，以后类似情况要提前声明。