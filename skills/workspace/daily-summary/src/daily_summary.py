#!/usr/bin/env python3
"""
每日汇报 - 对话记录汇总脚本
功能：
  1. 搜索指定日期的对话记录
  2. 生成本地 Markdown 汇报文件（可选存档）
  3. 输出格式化汇报内容供 Agent 直接展示给用户
"""

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent
CONFIG_FILE = SKILL_DIR / "config" / "config.json"


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_date_arg(raw: str) -> str:
    """从用户输入中解析目标日期，默认今天。"""
    if not raw or raw.strip() == "":
        return datetime.now().strftime("%Y-%m-%d")

    m = re.search(r"(\d{2,4})[-/](\d{2})[-/](\d{2})", raw)
    if not m:
        return datetime.now().strftime("%Y-%m-%d")

    year_part, month, day = m.group(1), m.group(2), m.group(3)

    if len(year_part) == 2:
        year = datetime.now().strftime("%Y")[:2] + year_part
    else:
        year = year_part

    return f"{year}-{month}-{day}"


def call_workbuddy_conversation_search(date_str: str, days_range: int = 1) -> dict:
    """
    生成 conversation_search 工具的调用参数。
    返回格式化的 dict。
    """
    end_date = date_str
    start_date = (datetime.strptime(date_str, "%Y-%m-%d") - timedelta(days=days_range - 1)).strftime("%Y-%m-%d")
    return {
        "start_date": start_date,
        "end_date": end_date,
        "limit": 30,
        "query": f"{date_str}全部对话记录"
    }


def build_summary_content(date_str: str, conversations: list) -> str:
    """
    构建格式化汇报内容（Markdown 格式），供 Agent 直接展示给用户。
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        f"📅 {date_str} 每日汇报\n",
        f"🤖 AI 助手（Javis）工作日志\n",
    ]

    if not conversations:
        lines.append("⚠️ 未能获取到该日期的对话记录。")
        return "\n".join(lines)

    # 按 updated_at 排序（早→晚）
    sorted_conv = sorted(conversations, key=lambda x: x.get("updated_at", ""))

    # 分组
    groups = {
        "自动化任务": [],
        "飞书/文档操作": [],
        "数据查询": [],
        "系统配置": [],
        "其他": [],
    }

    for c in sorted_conv:
        summary = c.get("summary", "")
        updated = c.get("updated_at", "")[:16]
        conv_id = c.get("conversation_id", "")
        score = c.get("score", 0)

        entry = f"  • **[{updated}]** {summary}（ID: `{conv_id}`）"

        if any(k in summary for k in ["自动化", "automation", "每日", "脚本", "执行"]):
            groups["自动化任务"].append(entry)
        elif any(k in summary for k in ["飞书", "文档", "lark", "feishu", "多维表格", "base"]):
            groups["飞书/文档操作"].append(entry)
        elif any(k in summary for k in ["股票", "财经", "基金", "数据", "行情", "查询"]):
            groups["数据查询"].append(entry)
        elif any(k in summary for k in ["配置", "setup", "安装", "skill", "模型"]):
            groups["系统配置"].append(entry)
        else:
            groups["其他"].append(entry)

    emoji_map = {
        "自动化任务": "📌",
        "飞书/文档操作": "📄",
        "数据查询": "📊",
        "系统配置": "🤖",
        "其他": "📎",
    }

    for group_name, entries in groups.items():
        if not entries:
            continue
        emoji = emoji_map.get(group_name, "📎")
        lines.append(f"{emoji} **{group_name}**")
        for e in entries:
            lines.append(e)
        lines.append("")

    # 待办事项
    lines.append("📎 **待处理事项**")
    pending = [c for c in sorted_conv if c.get("score", 0) < 0.65]
    if pending:
        for c in pending:
            lines.append(f"  ⚠️ {c.get('summary','')}")
    else:
        lines.append("  ✅ 暂无明显待处理事项")

    lines.append("")
    lines.append(f"*本报告由 Javis AI 助手自动生成 | {now}*")

    return "\n".join(lines)


def main(raw_args: str = ""):
    """主入口。raw_args 为用户原始输入字符串。"""
    date_str = parse_date_arg(raw_args)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 构建查询参数供 Agent 调用 conversation_search
    search_params = call_workbuddy_conversation_search(date_str)

    print(f"[每日汇报] 目标日期: {date_str}")
    print(f"[每日汇报] 搜索参数: {json.dumps(search_params, ensure_ascii=False)}")
    print("[每日汇报] 调用 conversation_search 获取对话数据后，直接在对话框输出格式化汇报内容。")

    return 0


if __name__ == "__main__":
    args = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else ""
    sys.exit(main(args))
