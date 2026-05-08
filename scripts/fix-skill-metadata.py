#!/usr/bin/env python3
"""批量为自定义 skills 补充 SKILL.md front matter 元数据"""

import os
import re
import yaml

SKILLS_DIR = '/root/.openclaw/workspace/skills'

# 需要跳过的目录（非 skill）
SKIP_DIRS = {'.skills_store_lock.json', 'skills'}

def get_description_from_content(content):
    """从 SKILL.md 内容中提取 description"""
    # 尝试从标题行提取
    lines = content.strip().split('\n')
    for i, line in enumerate(lines[:10]):
        # 跳过 front matter 开始标记
        if line.strip().startswith('---'):
            continue
        # 第一行通常是标题 #
        if line.startswith('# '):
            desc_line = lines[i+1].strip() if i+1 < len(lines) else ''
            # 第二行可能是简短描述
            if desc_line and not desc_line.startswith('#') and len(desc_line) < 200:
                return desc_line
            return line.lstrip('#').strip()
    return ''

def has_front_matter(content):
    """检查是否已有 front matter"""
    return content.strip().startswith('---')

def extract_front_matter(content):
    """提取并解析 front matter"""
    if not content.strip().startswith('---'):
        return None
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None
    try:
        return yaml.safe_load(parts[1])
    except:
        return None

def add_front_matter(content, name, description):
    """添加/更新 front matter"""
    front_matter = {
        'name': name,
        'description': description
    }
    fm_yaml = yaml.dump(front_matter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    # 移除结尾的 ...
    fm_yaml = fm_yaml.strip()
    
    if has_front_matter(content):
        # 替换现有 front matter
        parts = content.split('---', 2)
        return f"---\n{fm_yaml}\n---\n{parts[2]}"
    else:
        return f"---\n{fm_yaml}\n---\n\n{content}"

def process_skill(name, skill_path):
    """处理单个 skill"""
    skill_md = os.path.join(skill_path, 'SKILL.md')
    if not os.path.exists(skill_md):
        return False, f"  SKIP: {name} (无 SKILL.md)"
    
    with open(skill_md, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已有完整的 front matter
    fm = extract_front_matter(content)
    if fm and fm.get('name') and fm.get('description'):
        return True, f"  OK:   {name} (已有完整 front matter)"
    
    # 提取 description
    description = ''
    if fm and fm.get('description'):
        description = fm['description']
    else:
        description = get_description_from_content(content)
    
    if not description:
        return False, f"  FAIL: {name} (无法提取 description)"
    
    # 写入更新
    new_content = add_front_matter(content, name, description)
    with open(skill_md, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    return True, f"  ADD:  {name} → {description[:50]}..."

if __name__ == '__main__':
    skills_dir = SKILLS_DIR
    results = {'ok': 0, 'skip': 0, 'fail': 0, 'details': []}
    
    for name in sorted(os.listdir(skills_dir)):
        if name in SKIP_DIRS or name.startswith('.'):
            continue
        skill_path = os.path.join(skills_dir, name)
        if not os.path.isdir(skill_path):
            continue
        
        ok, msg = process_skill(name, skill_path)
        results['details'].append(msg)
        if ok:
            results['ok'] += 1
        else:
            results['fail'] += 1
    
    print(f"处理完成: {results['ok']} 成功, {results['fail']} 失败")
    print()
    for msg in results['details']:
        print(msg)
