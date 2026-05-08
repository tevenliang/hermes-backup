---
name: company-search
description: 公司信息查询技能。当用户说"查一下这家公司"、"搜索公司信息"、"查询公司"、"帮我了解一下这家公司"时激活。
---

# 查公司技能

## 功能说明

**仅负责查询，不负责录入。** 工作流程：

1. **从飞书 My Customer 表格查询**（模糊搜索 Customer 字段）
2. **如果已存在** → 返回该公司的完整记录内容
3. **如果不存在** → 告知用户"表格中没有该公司"，询问是否需要全网搜索
4. **用户确认要搜索** → 全网搜索并返回结果

---

## 查询方法

**使用 MCP 工具**（lark-mcp），查询参数：

```
mcp_lark_mcp_bitable_v1_appTableRecord_search
- app_token: BO6kb2c7haHY2FsLJCecH1mrnhe
- table_id: tblDEBAW1NOq61Ch
- automatic_fields: true
- filter: {"conjunction":"or", "conditions":[{"field_name":"Customer","operator":"contains","value":[查询关键词]}]}
```

**关键**：必须使用 `automatic_fields: true`，这样会返回所有字段的全部内容，不需要也不应该手动指定 field_names。

**备选：lark-cli**（MCP 不可用时）：
```bash
lark-cli api POST /open-apis/bitable/v1/apps/BO6kb2c7haHY2FsLJCecH1mrnhe/tables/tblDEBAW1NOq61Ch/records/search \
  --data '{"filter":{"conjunction":"or","conditions":[{"field_name":"Customer","operator":"contains","value":["公司名"]}]},"automatic_fields":true,"page_size":5}'
```

---

## 字段名（2026-05-04 纠正）

以下字段名是错的，不要再写：
- ❌ `企业简介` → ✅ `公司简介`
- ❌ `Contacts` = `企业信息收集` → ✅ 是两个**独立字段**，内容不同

正确字段列表（25个，去掉不展示的）：

| 字段名 | 类型 | 说明 |
|--------|------|------|
| `Customer` | Text（主键） | 公司名称，用于模糊搜索 |
| `行业` | SingleSelect | 行业分类 |
| `Stage` | SingleSelect | 销售阶段 |
| `Tag` | MultiSelect | 标签 |
| `Contacts` | Text | 联系人、股东、联系方式（**≠企业信息收集**） |
| `Log` | Text | 沟通日志 |
| `Summary` | Text | 摘要 |
| `Files` | Text | 附件（返回 token，需拼 URL） |
| `Due` | DateTime | 截止日期 |
| `Action` | Text | 行动记录 |
| `公司简介` | Text | 公司简介 |
| `产品服务` | Text | 产品服务描述 |
| `财务状况` | Text | 财务状况描述 |
| `下游` | Text | 下游客户 |
| `营收` | Number | 营收数字 |
| `人数` | Number | 员工人数 |
| `网站` | Text | 官网 |
| `地址` | Text | 公司地址 |
| `竞争对手` | Text | 竞争对手 |
| `城市` | Text | 城市 |
| `企业信息收集` | Text | 尽职调查信息（**独立字段，不展示**） |
| `创建日期` | DateTime | 记录创建日期（毫秒时间戳） |
| `企业新闻` | Url | 新闻链接（返回 token 格式） |
| `企业新闻最后更新` | DateTime | 新闻更新时间 |

---

## 返回数据结构的判断（2026-05-04 实测）

| 字段类型 | API 返回格式 | 处理方式 |
|---------|-------------|---------|
| Text/多行文本 | `[{"type":"text","text":"..."}]` | 取 `.text` |
| Text（含 URL） | `[{"type":"url","link":"...","text":"..."}]` | 取 `.link` 作为 URL |
| SingleSelect | `"值"`（直接字符串） | 直接用 |
| MultiSelect | `["值1","值2"]`（数组） | 直接用 |
| Number | `123`（数字） | 直接用 |
| DateTime | `1774972800000`（毫秒） | ÷1000，转 `yyyy-MM-dd` |
| Url | `[{"type":"url","link":"...","text":"..."}]` | 取 `.link` |
| Mention/Docx | `[{"type":"mention","token":"xxx"}]` | 拼 URL：`https://my.feishu.cn/docx/{token}` |

**空字段判断**：API 里该 key 不存在，不是 null。判断空要这样写：`if "field_name" not in record["fields"]` 或 `"field_name" in record["fields"] and record["fields"]["field_name"]`。

---

## 返回记录内容

使用 `automatic_fields: true` 返回后，按以下规则处理字段并输出：

**不显示的字段**（内部字段，不需要用户看）：
- `查重❗` — 自动公式字段，不展示
- `企业信息收集` — 内容过长且已合并到上面的字段中，不重复展示

**其余所有字段全部展示**，格式如下：

| 字段 | 值 |
|------|-----|
| **Customer** | [公司名] |
| **行业** | [行业] |
| **Stage** | [阶段] |
| **Tag** | [标签] |
| **营收** | [数字]亿元（年份） |
| **人数** | [数字] |
| **网站** | [URL] |
| **地址** | [地址] |
| **创建日期** | [日期] |

**公司简介**：[文本]

**产品服务**：[文本]

**下游**：[文本]

**竞争对手**：[文本]

**财务状况**：[文本]

**Contacts**：[文本，含联系人姓名、电话、邮箱、职务]

**Log**：[文本]（如无则标注"（空）"）

**Summary**：[文本]（如无则标注"（空）"）

**Files**：[文本]（如无则标注"（空）"）

**Due**：[日期]（如无则标注"（空）"）

**Action**：[文本]（如无则标注"（空）"）

**企业新闻**：[URL，如无则标注"（空）"]

**企业新闻最后更新**：[日期]（如无则标注"（空）"）

**城市**：[文本]（如无则标注"（空）"）

---

**空字段处理**：输出时标注"（空）"，不做删减。

---

## 公司不存在 → 询问是否搜索

告知用户："表格中没有该公司，是否需要全网搜索？"

用户确认后 → 使用 Tavily 搜索 → 返回结果

---

## 搜索方法

**使用 Tavily 搜索**：
```
mcp_minimax_web_search(query="[公司名称] 企业信息 注册资本 官网 行业 简介")
```

---

## 查表失败处理

**MCP 查询可能的错误**：

| 错误码 | 含义 | 处理 |
|--------|------|------|
| `1254045 FieldNameNotFound` | 字段名拼写错误 | 使用 automatic_fields: true，不手动指定字段名 |
| `99991679` | 权限不足 | 确认 bitable:app 权限已在飞书开放平台开通 |
| `Client network socket disconnected` | 网络抖动 | 重试一次 |

---

## 工作流程（强制顺序）

```
Step 1: MCP 查询 bitable（automatic_fields: true，模糊搜索 Customer）
    ↓
Step 2a: 查到了 → 返回完整记录（25个字段全部列出，空字段标"（空）"）
    ↓
Step 2b: 查不到（total=0）→ 告知用户"表格中没有该公司"，问"是否需要全网搜索？"
    ↓
Step 2c: 网络/权限报错 → 重试一次，无效则告知用户
```

---

## 飞书多维表格字段结构参考

**详细字段类型、返回数据结构、空字段行为见**：`references/feishu-bitable-fields.md`

关键提醒：
- **空字段在 API 中不返回 key**，不是返回 null/空字符串
- **Contacts ≠ 企业信息收集**，两个独立字段
- **Files/Mention 字段**返回飞书文档 token，需转为 `https://my.feishu.cn/docx/{token}` 才能访问
- **DateTime 字段**是毫秒时间戳，需 ÷1000 后转换

---

## 已知陷阱

1. **必须用 automatic_fields: true**：飞书多维表格字段名是中文（如`公司简介`、`Contacts`、`企业信息收集`），手动指定 field_names 容易遗漏字段或拼错。
2. **Contacts ≠ 企业信息收集**：这是两个独立字段，内容完全不同。Contacts 是联系人信息，企业信息收集是尽职调查问答。
3. **空字段在 API 里是"不返回 key"**：代码里判断空字段要检查 key 是否存在，不要写成 `fields.字段名 === ""`（永远不成立）。
4. **不擅自切换搜索**：表格查不到时必须询问用户，不自动改为全网搜索。
5. **Files/Mention 字段需要转换**：飞书文档 token 需拼成 `https://my.feishu.cn/docx/{token}` 才能访问。
4. **不擅自切换搜索**：表格查不到时必须询问用户，不自动改为全网搜索。
