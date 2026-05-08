#!/usr/bin/env python3
"""
每日AI动态 - 飞书文档追加脚本
自动追加当日简报内容到飞书文档
"""

import json
import sys
import os
from datetime import datetime

# 飞书文档配置
DOC_TOKEN = "Rr1ndLna1olwWzxZKS6c6Vl1nCd"
APP_ID = "cli_a947b541d8785bd9"
APP_SECRET = "HAxArnZY8IDYuS5057mwtbNm3Vo4jqd1"

# 飞书 API 地址
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
DOC_URL = "https://open.feishu.cn/open-apis/doc/v1/documents/{doc_token}/blocks/{block_id}/children"

def get_tenant_token():
    """获取 tenant access token"""
    resp = os.popen(f'''curl -s -X POST "{TOKEN_URL}" \
        -H "Content-Type: application/json" \
        -d '{{"app_id":"{APP_ID}","app_secret":"{APP_SECRET}"}}' ''').read()
    data = json.loads(resp)
    return data.get("tenant_access_token", "")

def append_blocks(token, blocks):
    """追加 block 到文档"""
    # 先获取文档根 blocks，找到最后一个 block
    list_url = f"https://open.feishu.cn/open-apis/doc/v1/documents/{DOC_TOKEN}/blocks"
    
    resp = os.popen(f'''curl -s -X GET "{list_url}" \
        -H "Authorization: Bearer {token}" \
        -H "Content-Type: application/json" ''').read()
    
    try:
        data = json.loads(resp)
        items = data.get("data", {}).get("items", [])
        # 找到最后一个子 block 的 block_id
        last_block_id = items[-1]["block_id"] if items else DOC_TOKEN
    except:
        last_block_id = DOC_TOKEN
    
    # 追加内容
    url = f"https://open.feishu.cn/open-apis/doc/v1/documents/{DOC_TOKEN}/blocks/{last_block_id}/children"
    
    payload = {
        "children": blocks,
        "index": -1
    }
    
    cmd = f'''curl -s -X POST "{url}" \
        -H "Authorization: Bearer {token}" \
        -H "Content-Type: application/json" \
        -d '{json.dumps(payload, ensure_ascii=False)}' '''
    
    resp = os.popen(cmd).read()
    return json.loads(resp)

def build_blocks(date_str, briefing_content):
    """构建要追加的 blocks"""
    blocks = []
    
    # 日期标题 (Heading2)
    blocks.append({
        "block_type": 4,
        "heading2": {
            "elements": [{"text_run": {"content": f"📅 {date_str}"}}],
            "style": {"align": 1, "folded": False}
        }
    })
    
    # 各板块内容
    sections = [
        ("☁️ AWS AI", briefing_content.get("aws", ["（暂无动态）"])),
        ("🔵 Azure AI", briefing_content.get("azure", ["（暂无动态）"])),
        ("🌐 Google Cloud AI", briefing_content.get("gcp", ["（暂无动态）"])),
        ("🇨🇳 中国云厂商 AI", briefing_content.get("cn", ["（暂无动态）"])),
        ("🐙 竞品动态 (GitHub / GitLab)", briefing_content.get("competitors", ["（暂无动态）"])),
    ]
    
    for section_title, items in sections:
        # 小标题 (Heading3)
        blocks.append({
            "block_type": 5,
            "heading3": {
                "elements": [{"text_run": {"content": section_title}}],
                "style": {"align": 1, "folded": False}
            }
        })
        
        # 列表项 (Bullet)
        for item in items:
            blocks.append({
                "block_type": 12,
                "bullet": {
                    "elements": [{"text_run": {"content": item}}],
                    "style": {"align": 1, "folded": False}
                }
            })
    
    # 分隔线
    blocks.append({
        "block_type": 22,
        "divider": {}
    })
    
    # 更新时间
    blocks.append({
        "block_type": 2,
        "text": {
            "elements": [{"text_run": {"content": f"由贾维斯自动生成 {datetime.now().strftime('%Y-%m-%d %H:%M')}", "text_element_style": {"italic": True}}}],
            "style": {"align": 1, "folded": False}
        }
    })
    
    return blocks

def main():
    if len(sys.argv) < 2:
        # 从默认的每日简报文件读取
        date_str = datetime.now().strftime("%Y-%m-%d")
        briefing_file = f"/root/.openclaw/workspace/daily-briefings/{date_str}-ai-briefing.md"
        
        if os.path.exists(briefing_file):
            with open(briefing_file, "r") as f:
                content = f.read()
        else:
            # 如果没有文件，使用默认内容
            content = {
                "aws": ["（今日动态抓取中...）"],
                "azure": ["（今日动态抓取中...）"],
                "gcp": ["（今日动态抓取中...）"],
                "cn": ["（今日动态抓取中...）"],
                "competitors": ["（今日动态抓取中...）"]
            }
    else:
        # 解析命令行参数的 JSON 内容
        try:
            content = json.loads(sys.argv[1])
        except:
            content = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    
    # 日期
    if isinstance(content, dict):
        briefing = content
    else:
        briefing = {
            "aws": ["（今日动态抓取中...）"],
            "azure": ["（今日动态抓取中...）"],
            "gcp": ["（今日动态抓取中...）"],
            "cn": ["（今日动态抓取中...）"],
            "competitors": ["（今日动态抓取中...）"]
        }
    
    date_str = sys.argv[2] if len(sys.argv) > 2 else datetime.now().strftime("%Y-%m-%d")
    
    # 获取 token
    token = get_tenant_token()
    if not token:
        print("❌ 获取飞书 token 失败")
        sys.exit(1)
    
    # 构建 blocks
    blocks = build_blocks(date_str, briefing)
    
    # 追加到文档
    result = append_blocks(token, blocks)
    
    if result.get("code") == 0:
        print(f"✅ 成功追加内容到飞书文档")
    else:
        print(f"❌ 追加失败: {result}")

if __name__ == "__main__":
    main()
