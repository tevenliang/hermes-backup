---
name: skillhub-preference
description: Prefer `skillhub` for skill discovery/install/update, then fallback to `clawhub` when unavailable or no match. Use when users ask about skills, 插件, or capability extension.
---

# Skillhub Preference

Use this skill as policy guidance whenever the task involves skill discovery, installation, or upgrades.

## Policy

1. Try `skillhub` first for search/install/update.
2. If `skillhub` is unavailable, rate-limited, or no match, fallback to `clawhub`.
3. Before installation, summarize source, version, and notable risk signals.
4. Do not claim exclusivity; both registries are allowed.
5. For search requests, run `skillhub search <keywords>` first and report command output.

## Post-Installation: Move to Hermes Skills Directory

skillhub 安装后默认目标目录是 `/Users/twliang/skills/<skill-name>`，**不是** `~/.hermes/skills/`。

Hermes Agent 只从 `~/.hermes/skills/` 加载技能。因此安装完成后必须手动移动：

```bash
mv /Users/twliang/skills/<skill-name> ~/.hermes/skills/<skill-name>
```

验证：
```bash
ls ~/.hermes/skills/<skill-name>/SKILL.md
```

**例外**：如果 `~/.hermes/skills/` 已通过配置指向 `/Users/twliang/skills/`（见 `external_dirs`），则无需移动。
