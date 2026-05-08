#!/usr/bin/env python3
"""
每日聊天总结脚本
- 读取今日对话记录，生成摘要
- 写入飞书文档
- 推送飞书消息
"""
import json, urllib.request, os, glob, re
from datetime import datetime, timedelta

FEISHU_APP_ID = "cli_a947b541d8785bd9"
FEISHU_APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"
FEISHU_USER_ID = "ou_d4b39b86c8715f79b2c5b070c4e55393"
FEISHU_DOC_TOKEN = "Kq82du2e7omt25xtbOlcn0wEn9d"  # 每日聊天总结文档

SESSION_DIR = "/root/.openclaw/agents/main/sessions"
# 改为抓取昨日消息（cron在08:00运行，session文件包含前日晚间消息）
YESTERDAY = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
TODAY = YESTERDAY

# ==================== 飞书基础 ====================

def get_token():
    data = json.dumps({"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}).encode()
    req = urllib.request.Request(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        data=data, method="POST"
    )
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=15)
    return json.loads(resp.read())["tenant_access_token"]

def send_feishu(message):
    try:
        token = get_token()
        payload = json.dumps({
            "receive_id": FEISHU_USER_ID,
            "msg_type": "text",
            "content": json.dumps({"text": message})
        }).encode()
        req = urllib.request.Request(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
            data=payload, method="POST"
        )
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read()).get("code") == 0
    except Exception as e:
        print(f"  飞书发送失败: {e}")
        return False

def get_doc_root_id(doc_token, token):
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks?page_size=50"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    resp = urllib.request.urlopen(req, timeout=15)
    items = json.loads(resp.read()).get("data", {}).get("items", [])
    if not isinstance(items, list):
        return doc_token
    roots = [b for b in items if b.get("parent_id") == "" or b.get("parent_id") == doc_token]
    return roots[0]["block_id"] if roots else doc_token

def clear_doc_content(doc_token, token):
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks?page_size=100"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    resp = urllib.request.urlopen(req, timeout=15)
    items = json.loads(resp.read()).get("data", {}).get("items", [])
    if not isinstance(items, list):
        return
    roots = [b for b in items if b.get("parent_id") == "" or b.get("parent_id") == doc_token]
    root_ids = [b["block_id"] for b in roots]
    for block_id in root_ids:
        del_url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{block_id}"
        del_req = urllib.request.Request(del_url, method="DELETE")
        del_req.add_header("Authorization", f"Bearer {token}")
        try:
            urllib.request.urlopen(del_req, timeout=10)
        except:
            pass

def append_blocks(doc_token, blocks, token):
    root_id = get_doc_root_id(doc_token, token)
    url = f"https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks/{root_id}/children"
    payload = json.dumps({"children": blocks, "index": -1}).encode()
    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read()).get("code") == 0

# ==================== 对话读取 ====================

def find_today_sessions():
    """找到今日最新的 session 文件"""
    today_prefix = TODAY.replace("-", "")
    session_files = glob.glob(f"{SESSION_DIR}/*.jsonl")
    # 按修改时间排序
    session_files.sort(key=os.path.getmtime, reverse=True)
    for f in session_files:
        mtime = datetime.fromtimestamp(os.path.getmtime(f))
        if mtime.strftime("%Y-%m-%d") == TODAY and ".lock" not in f:
            return f
    # 找不到今天的，用最新的
    for f in session_files:
        if ".lock" not in f:
            return f
    return None

def extract_messages(session_file):
    """从 session 文件中提取今日用户消息"""
    if not session_file or not os.path.exists(session_file):
        return []

    messages = []

    with open(session_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                # 检查时间戳是否是今天
                ts = entry.get("timestamp", "")
                if ts:
                    msg_date = ts[:10]  # "2026-04-03T..."
                    if msg_date != TODAY:
                        continue

                # 找 type=message 的条目，里面的 message.role == "user"
                if entry.get("type") == "message":
                    inner = entry.get("message", {})
                    if inner.get("role") == "user":
                        content = inner.get("content", "")
                        text = ""
                        if isinstance(content, list):
                            for part in content:
                                if isinstance(part, dict):
                                    if part.get("type") == "text":
                                        text += part.get("text", "")
                                    elif part.get("type") == "audio":
                                        text += "[语音]"
                        elif isinstance(content, str):
                            text = content
                        else:
                            text = str(content)

                        # 过滤系统消息
                        if text and "[om_" not in text and not text.startswith("HEARTBEAT"):
                            messages.append(text[:300])
            except:
                pass

    return messages

# ==================== 主题分析 ====================

def analyze_topics(messages):
    """分析对话主题"""
    topic_map = {
        "🏢 公司调研": ["查公司", "调研", "录入", "客户"],
        "📊 财经": ["基金", "净值", "持仓", "股票", "ETF", "QDII"],
        "📋 资讯": ["日报", "资讯", "新闻", "搜索", "OpenClaw", "飞书"],
        "⚙️ 系统": ["脚本", "cron", "推送", "定时", "修复", "更新"],
        "⏰ 提醒": ["提醒", "日程", "安排"],
        "📧 Outlook": ["Outlook", "邮件", "日历", "待办"],
    }

    found = set()
    for msg in messages:
        msg_lower = msg.lower()
        for topic, keywords in topic_map.items():
            if any(k.lower() in msg_lower for k in keywords):
                found.add(topic)

    return list(found) if found else ["💬 一般对话"]

def generate_summary(messages, topics):
    """生成文字摘要"""
    count = len(messages)
    topic_str = " | ".join(topics)

    topic_descriptions = {
        "🏢 公司调研": "公司调研、信息录入、CRM操作",
        "📊 财经": "基金净值、持仓股票、市场动态",
        "📋 资讯": "资讯搜索、文档写入、AI简报",
        "⚙️ 系统": "脚本修复、cron配置、系统更新",
        "⏰ 提醒": "日程安排、提醒设置",
        "📧 Outlook": "邮件日历同步、待办管理",
        "💬 一般对话": "日常问答、工具咨询",
    }

    content_desc = "、".join([topic_descriptions.get(t, t) for t in topics])

    summary = f"""📝 今日贾维斯工作汇总

📅 {TODAY}
🏷️ 主题：{topic_str}
💬 对话：{count}条

内容涵盖：
• {content_desc}

明天继续加油！💪"""

    return summary

def build_doc_blocks(summary, topics, messages):
    """构建飞书文档 blocks"""
    blocks = []

    # 大标题
    blocks.append({
        "block_type": 3,
        "heading1": {
            "elements": [{"text_run": {"content": f"📝 每日聊天总结 — {TODAY}"}}],
            "style": {"align": 1, "folded": False}
        }
    })
    blocks.append({
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {"content": f"由贾维斯自动生成 | 主题：{' '.join(topics)}", "text_element_style": {"bold": True}}}],
            "style": {"align": 1, "folded": False}
        }
    })
    blocks.append({"block_type": 22, "divider": {}})

    # 摘要
    blocks.append({
        "block_type": 4,
        "heading2": {
            "elements": [{"text_run": {"content": "📌 今日摘要"}}],
            "style": {"align": 1, "folded": False}
        }
    })

    lines = summary.split('\n')
    for line in lines:
        if line.strip():
            blocks.append({
                "block_type": 2,
                "text": {
                    "elements": [{"text_run": {"content": line}}],
                    "style": {"align": 1, "folded": False}
                }
            })

    blocks.append({"block_type": 22, "divider": {}})

    # 消息列表
    blocks.append({
        "block_type": 4,
        "heading2": {
            "elements": [{"text_run": {"content": f"📋 对话记录（共 {len(messages)} 条）"}}],
            "style": {"align": 1, "folded": False}
        }
    })

    for i, msg in enumerate(messages[-20:], 1):  # 最多20条
        blocks.append({
            "block_type": 2,
            "text": {
                "elements": [{"text_run": {"content": f"{i}. {msg[:150]}"}}],
                "style": {}
            }
        })

    blocks.append({"block_type": 22, "divider": {}})
    blocks.append({
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {"content": f"🤖 由贾维斯自动生成 {datetime.now().strftime('%Y-%m-%d %H:%M')}", "text_element_style": {"italic": True}}}],
            "style": {"align": 1, "folded": False}
        }
    })

    return blocks

# ==================== 主程序 ====================

def main():
    print(f"📝 生成每日聊天总结... ({TODAY})")

    # 1. 找 session
    session_file = find_today_sessions()
    print(f"  使用 session: {session_file}")

    # 2. 读消息
    messages = extract_messages(session_file)
    print(f"  读取到 {len(messages)} 条消息")

    if not messages:
        print("  没有今日消息，尝试最近一次 session...")
        messages = extract_messages(session_file)
        if not messages:
            print("❌ 仍无消息，跳过")
            return

    # 3. 分析主题
    topics = analyze_topics(messages)
    print(f"  主题: {topics}")

    # 4. 生成摘要
    summary = generate_summary(messages, topics)
    print(f"\n{summary}")

    # 5. 写飞书文档
    print(f"\n📝 写入飞书文档...")
    token = get_token()
    ok_doc = write_doc(summary, topics, messages, token)
    print(f"  {'✅' if ok_doc else '❌'} 文档写入: {'成功' if ok_doc else '失败'}")

    # 6. 发飞书消息
    print(f"📱 发送飞书...")
    # 截断到5000字
    msg_to_send = summary if len(summary) < 5000 else summary[:5000] + "\n\n...（内容过长已截断）"
    ok = send_feishu(msg_to_send)
    print(f"  {'✅' if ok else '❌'} 飞书推送: {'成功' if ok else '失败'}")

    print(f"\n✅ 完成 {datetime.now().strftime('%Y-%m-%d %H:%M')}")


def write_doc(summary, topics, messages, token):
    blocks = build_doc_blocks(summary, topics, messages)
    clear_doc_content(FEISHU_DOC_TOKEN, token)
    return append_blocks(FEISHU_DOC_TOKEN, blocks, token)


if __name__ == "__main__":
    main()
