# lark-cli --markdown stdin 方式

## 关键发现

`lark-cli docs +create --markdown` 对文件路径的解析有歧义：
- 传入绝对路径（如 `/tmp/xxx.md`）✅ 可以读取
- 传入 `@skills/xxx.md` 相对路径 ❌ 解析失败，找不到文件
- 传入 `-` 从 stdin 读取 ✅ 可靠

## 正确用法

```bash
# ✅ 推荐：stdin 方式
cat /path/to/content.md | lark-cli docs +create \
  --as user \
  --title "文档标题" \
  --folder-token <folder_token> \
  --markdown -

# ✅ 可用：绝对路径
lark-cli docs +create \
  --as user \
  --title "文档标题" \
  --folder-token <folder_token> \
  --markdown /absolute/path/to/content.md

# ❌ 失败：相对路径（含 @前缀）
lark-cli docs +create --markdown "@skills/customer_news_tmp.md"  # 文件找不到
```

## 为什么

lark-cli 的 `--markdown @file` 使用 `openclaw` workspace 相对路径解析，不在同一个 workspace 目录下时解析失败。stdin 方式绕过路径解析，最可靠。

## 适用命令

任何 `--markdown` 参数都适用同样的模式：
```bash
cat file.md | lark-cli docs +create ... --markdown -
```
