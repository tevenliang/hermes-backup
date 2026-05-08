# Skill 目录迁移安全检查清单

**触发条件：任何 skill 目录被移动、重命名、或迁移到新路径之后，必须执行以下全部步骤。**

---

## 步骤一：确认 skill 可被找到

```bash
hermes skills list | grep <skill-name>
```

显示 `enabled` 即可。

---

## 步骤二：检查 SKILL.md 内部是否有硬编码旧路径

```bash
grep -n "~/.hermes/scripts/\|/workspace/\|/skills/" ~/.hermes/skills/<category>/<skill>/SKILL.md
```

找到任何旧路径立即 patch 为新路径。

---

## 步骤三：检查 cron job prompts 是否引用了该 skill 的脚本

```bash
cronjob list 2>/dev/null | grep -B2 -A5 "<skill-name>"
```

检查 `prompt_preview` 里的脚本路径是否仍指向旧目录。

**如果 prompt 里有 `~/.hermes/scripts/` 或旧 skill 路径 → 必须同步更新 cron job prompt。**

---

## 步骤四：确认脚本文件实际存在于新路径

```bash
ls ~/.hermes/skills/<new-category>/<skill>/scripts/
```

不存在则说明脚本可能还在旧目录或未跟随迁移。

---

## 关键教训

skill 绑定到 cron job 后，cron job prompt 里的脚本路径是**独立存储的**，不会随着 skill 目录迁移而自动更新。每次 skill 迁移必然需要同步更新 cron job prompt，否则 cron 实际调用失败但 skill 仍显示 enabled。

system-check 的 `~/.hermes/scripts/pc-health-check.sh` 路径问题已因此错了 3 次。
