# 飞书多维表格字段结构参考（客户数据表）

> 来源：2026-05-04 调用 `appTableField_list` API 实测
> app_token: `BO6kb2c7haHY2FsLJCecH1mrnhe`
> table_id: `tblDEBAW1NOq61Ch`

## 字段列表（共25个）

| # | 字段名 | 类型 | UI_Type | 说明 |
|---|--------|------|---------|------|
| 1 | Customer | Text | Text | 主键，公司名称 |
| 2 | 行业 | SingleSelect | SingleSelect | 选项：互联网/电子/制造业/汽车行业/医疗医药/新能源/金融/其它/半导体/机器人/电力/批发业/储能科技 |
| 3 | Stage | SingleSelect | SingleSelect | 选项：案例/存档/保持/潜在/建联/机会/赢单/新建 |
| 4 | Tag | MultiSelect | MultiSelect | 选项：KA/SMB/区域销售/东莞 |
| 5 | Contacts | Text | Text | 联系人和股东信息，含邮箱/电话 |
| 6 | Log | Text | Text | 沟通日志 |
| 7 | Summary | Text | Text | 摘要 |
| 8 | Files | Text | Text | 附件（飞书文档 token） |
| 9 | Due | DateTime | DateTime | 截止日期，格式 MM-dd |
| 10 | Action | Text | Text | 行动记录 |
| 11 | 公司简介 | Text | Text | 公司简介（注意不是"企业简介"） |
| 12 | 产品服务 | Text | Text | 产品服务描述 |
| 13 | 财务状况 | Text | Text | 财务状况描述 |
| 14 | 下游 | Text | Text | 下游客户 |
| 15 | 营收 | Number | Number | 营收数字（单位：亿元） |
| 16 | 人数 | Number | Number | 员工人数 |
| 17 | 网站 | Text | Text | 官网 URL |
| 18 | 地址 | Text | Text | 公司地址 |
| 19 | 竞争对手 | Text | Text | 竞争对手 |
| 20 | 城市 | Text | Text | 城市 |
| 21 | 企业信息收集 | Text | Text | 尽职调查信息（独立字段，与 Contacts 不同） |
| 22 | 创建日期 | DateTime | DateTime | 记录创建日期，格式 yyyy/MM/dd |
| 23 | 查重❗ | Formula | Formula | IF查重公式（不展示） |
| 24 | 企业新闻 | Url | Url | 新闻链接 URL |
| 25 | 企业新闻最后更新 | DateTime | DateTime | 新闻更新时间，格式 yyyy/MM/dd |

## 不同字段类型的返回数据结构

### Text 类型（含 URL 类型）
```json
// 普通文本
"Contacts": [{"type": "text", "text": "最大股东：贾奎占股（37.06%）\n"}]

// 可点击 URL（邮箱）
"Contacts": [
  {"type": "text", "text": "jiakui@dexforce.com"},
  {"link": "mailto:jiakui@dexforce.com", "type": "url", "text": "jiakui@dexforce.com"}
]

// URL 类型字段（企业新闻）
"企业新闻": [{"type": "url", "link": "https://example.com", "text": "新闻标题"}]
```

### SingleSelect / MultiSelect
```json
// SingleSelect：直接字符串
"Stage": "赢单"
"行业": "互联网"

// MultiSelect：数组
"Tag": ["KA"]
```

### Number
```json
"营收": 76.94
"人数": 300
```

### DateTime
```json
// 毫秒时间戳（需 ÷1000 后转换）
"创建日期": 1774972800000  // → 2026-01-29
```

### Files / Mention（飞书文档 token）
```json
"Files": [
  {
    "type": "mention",
    "token": "BDatdxUV8oz4Fux2ylBcOn8Rn1g",
    "text": "中邮消费金融沟通记录",
    "mentionType": "Docx",
    "realMentionType": "Docx"
  }
]
```
**转换为可访问链接**：`https://my.feishu.cn/docx/{token}`

## 空字段行为（关键）

**飞书 API 的空字段处理**：当字段在表格中为空时，API 响应中**完全不返回该字段的 key**，不是返回 `null`、空字符串或空数组。

```json
// 如果 企业信息收集 为空，API 返回：
{}  // 而不是 {"企业信息收集": ""} 或 {"企业信息收集": null}

// 如果 Files 为空，API 返回：
{}  // 而不是 {"Files": ""}
```

**判断空字段的正确方式**：检查 key 是否存在，不存在则为空。不要写成 `fields.企业信息收集 === ""`（永远不成立）。

## Contacts vs 企业信息收集（易混淆）

这是**两个不同字段**，内容完全不同：

| 字段 | 内容 |
|------|------|
| Contacts | 联系人姓名、电话、邮箱、职务、股东信息 |
| 企业信息收集 | 结构化的尽职调查信息（9个问答） |
