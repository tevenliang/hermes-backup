运行平台：MacBook本机 ~/.hermes/（2026-05-04起从VM迁移）
§
搜索内容规范：必须确保日期新鲜（用户期望最新，5月）。文章列表格式：标题+作者+精确日期+点赞/收藏数+摘要（2-3句具体内容）+原文链接，不接受纯标题列表。Xiaohongshu搜索用opencli > wechat-article-search（后者不返回正文摘要）。opencli-tool已安装且Browser Bridge已连接（2026-05-04）。
§
提醒规则（2026-05-06确认）：用户说"提醒我xxx" → 默认走 Apple Reminders（remindctl），只有用户明确说"定时任务"或"cron"时才创建 cron 任务。分类体系：工作、学习、生活 三个分类，不合并。创建任务时自动判断分类，默认不加截止日期，输出待办列表时带分类标签。
§
反复 patch 同一文件超过 3-4 轮会导致结构损坏（重复函数定义、缩进错乱）。遇到这类情况应重写整个文件，而非继续 patch。
§
不要每次本地文件修改后自动 push 到 GitHub，而是由 cron 任务每日午夜自动执行 git push（Job ID: 27a1c41d316c）。
§
API Key 管理与查找：飞书多维表格（账号密码表 `OvQ2bpM6gaez1ksDTYwclTPjnib/tblvdLBUJJbOouUy`）是唯一真实来源，运行时 key 写入系统配置文件，config 里 terminal.env_passthrough 注入。新增 key 流程：用户告知 → 我查表 → 写入运行时配置。Bot 对该多维表格仅有读权限，无写权限。查找优先级：先搜该表，搜不到再问用户。
§
执行任何任务前必须先加载对应 Skill，按 Skill 里的命令走，不能凭记忆或试错。
§
Skills 目录迁移后 cron prompt 路径不自动同步，每次 skill 迁移必须同步检查所有引用该脚本的 cron job prompts。
§
内容追踪多维表格（内容追踪（抖音/小红书/公众号））：app_token `NeDBbyQvTa0xdysDCbRcQZ8cnMf`，博主链接表 `tbl9cnCB9Hnjxuzb`，文章内容表 `tbllE5S5vOhj5W9x`，folder_token `K312fSiL0lApa8dLCARczd1jnUO`。用途：追踪抖音/小红书/公众号博主文章。
§
飞书操作：全面使用 lark-cli（Feishu CLI）替代 lark-mcp，禁止使用 feishu-mcp。参考：https://github.com/larksuite/cli
- 所有飞书操作（消息/多维表格/文档/日历等）统一用 lark-cli
- 多维表格：lark-cli base +record-list / +record-batch-create / +record-update
- 认证：lark-cli auth login --domain base（device code 方式）
- 身份：--as user（用户身份）/ --as bot（bot身份）
§
所有 Skills 中调用 feishu-mcp 的地方必须修改为 lark-cli 实现，feishu-mcp 已全面废弃。
§
抖音sec_uid（来源：用户确认的抖音分享链接 + 浏览器访问提取）:
- 口罩哥直播号: MS4wLjABAAAAO5TIp1flPZXvqelTSBPiwPbb8F7Lpf_PfCT8_xJRk0QuwS92L7dBVfR7W0M9rudR
- Trader韭: MS4wLjABAAAAHiP_Vgs58df2m_Z-FBgay8n2Y9DUOYY7IeeSqMWWplM
- 余承东: MS4wLjABAAAAc2QXCL5FCjz-Yb5X-p2Rcg6XfGmDDntzFmeDYuIZWljqowBW0vO78yXN4qt4Rk7P
- 数字游牧人Samuel: MS4wLjABAAAAcBGY4RqDTLberZGiFTk-nG_L0hVwrFC7Bii_20YdBgBDGu-9JoA2L6jtkpdnpBpr
- 跟着Mark学储蓄: MS4wLjABAAAAF5x8PfnPk7vT5aI5L2bD8rG_X3qWvN9dK2mC4hR6sTuQ1jF
- 宋鸿兵观天下: MS4wLjABAAAAzaye_V0qtP4d7m77UywUBRq7xB9CRiLaeGPfg79hLtQ
- 可喜: MS4wLjABAAAAX1iRjBCVyMg-xzgVp1_sm758gj_zTJA9FJJojwcWw0fr-WLAv13_rIkv7jhwIF33
- 创哥的AI实验室: MS4wLjABAAAAFR2-YXEXvVAcCX8_MiMRl3qsacsdXJiSdWm6AvCCU0k
博主表(NeDBbyQvTa0xdysDCbRcQZ8cnMf/tbl9cnCB9Hnjxuzb)字段: 序号/博主/主页链接/sec_uid(新建)