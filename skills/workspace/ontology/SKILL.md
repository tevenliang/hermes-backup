---
name: ontology
description: "Typed knowledge graph for structured agent memory. USE ONLY when data will be actively queried by the agent across sessions. NOT a replacement for task managers (Todoist/飞书Tasks), Feishu bitables, or note tools — those already exist and should stay as the source of truth. Best for: cross-session project state, entity relationships that feed agent decisions, and commitments the agent should track autonomously. Trigger conservatively: only when no existing tool covers the use case."
---

# Ontology

A typed vocabulary + constraint system for representing knowledge as a verifiable graph.

## Core Concept

Everything is an **entity** with a **type**, **properties**, and **relations** to other entities. Every mutation is validated against type constraints before committing.

```
Entity: { id, type, properties, relations, created, updated }
Relation: { from_id, relation_type, to_id, properties }
```

## When NOT to Use

❌ **You already have a task manager** (飞书Tasks, Todoist, etc.) → use it for tasks
❌ **You already manage companies/contacts in Feishu bitable** → use it for companies and people
❌ **You want to archive data for humans to read** → use Feishu docs instead
❌ **The data will only be written, never actively queried** → this creates a "data graveyard"

**The test:** Before writing to ontology, ask: "What will call this query?" If the answer is "nobody" or "only when a human manually asks," store it in Feishu instead.

## When to Use

| Trigger | Action |
|---------|--------|
| Cross-session project continuity | Create/update entity |
| Agent needs to know "where we left off" | Query graph |
| Link entity A to entity B for traversal queries | Create relation |
| Agent should autonomously track a commitment | Create entity + set follow-up |

## Known Limitations

- Python 3.9.6 syntax error on `Path | None` union syntax. Use `from typing import Optional; root: Optional[Path] = None` instead.
- Append-only storage: never overwrite graph.jsonl, only append operations.
- Higher-level constraints (e.g., Task status transitions) are documentation-only unless enforced in code.

## Workflows

## 已知问题

**Python 3.9.6 语法错误（TypeError: unsupported operand）**

`scripts/ontology.py` 第 29 行使用了 Python 3.10+ 的联合类型标注语法：
```python
root: Path | None = None   # TypeError on Python 3.9.6
```

修复：改为
```python
from typing import Optional
root: Optional[Path] = None
```

MacBook 上 Python 版本为 3.9.6，执行 `ontology.py` 相关命令前必须确认已修复此语法问题。

```yaml
# Agents & People
Person: { name, email?, phone?, notes? }
Organization: { name, type?, members[] }

# Work
Project: { name, status, goals[], owner? }
Task: { title, status, due?, priority?, assignee?, blockers[] }
Goal: { description, target_date?, metrics[] }

# Time & Place
Event: { title, start, end?, location?, attendees[], recurrence? }
Location: { name, address?, coordinates? }

# Information
Document: { title, path?, url?, summary? }
Message: { content, sender, recipients[], thread? }
Thread: { subject, participants[], messages[] }
Note: { content, tags[], refs[] }

# Resources
Account: { service, username, credential_ref? }
Device: { name, type, identifiers[] }
Credential: { service, secret_ref }  # Never store secrets directly

# Meta
Action: { type, target, timestamp, outcome? }
Policy: { scope, rule, enforcement }
```

## Storage

Default: `memory/ontology/graph.jsonl`

```jsonl
{"op":"create","entity":{"id":"p_001","type":"Person","properties":{"name":"Alice"}}}
{"op":"create","entity":{"id":"proj_001","type":"Project","properties":{"name":"Website Redesign","status":"active"}}}
{"op":"relate","from":"proj_001","rel":"has_owner","to":"p_001"}
```

Query via scripts or direct file ops. For complex graphs, migrate to SQLite.

### Append-Only Rule

When working with existing ontology data or schema, **append/merge** changes instead of overwriting files. This preserves history and avoids clobbering prior definitions.

## Workflows

### Create Entity

```bash
python3 scripts/ontology.py create --type Person --props '{"name":"Alice","email":"alice@example.com"}'
```

### Query

```bash
python3 scripts/ontology.py query --type Task --where '{"status":"open"}'
python3 scripts/ontology.py get --id task_001
python3 scripts/ontology.py related --id proj_001 --rel has_task
```

### Link Entities

```bash
python3 scripts/ontology.py relate --from proj_001 --rel has_task --to task_001
```

### Validate

```bash
python3 scripts/ontology.py validate  # Check all constraints
```

## Constraints

Define in `memory/ontology/schema.yaml`:

```yaml
types:
  Task:
    required: [title, status]
    status_enum: [open, in_progress, blocked, done]
  
  Event:
    required: [title, start]
    validate: "end >= start if end exists"

  Credential:
    required: [service, secret_ref]
    forbidden_properties: [password, secret, token]  # Force indirection

relations:
  has_owner:
    from_types: [Project, Task]
    to_types: [Person]
    cardinality: many_to_one
  
  blocks:
    from_types: [Task]
    to_types: [Task]
    acyclic: true  # No circular dependencies
```

## Skill Contract

Skills that use ontology should declare:

```yaml
# In SKILL.md frontmatter or header
ontology:
  reads: [Task, Project, Person]
  writes: [Task, Action]
  preconditions:
    - "Task.assignee must exist"
  postconditions:
    - "Created Task has status=open"
```

## Planning as Graph Transformation

Model multi-step plans as a sequence of graph operations:

```
Plan: "Schedule team meeting and create follow-up tasks"

1. CREATE Event { title: "Team Sync", attendees: [p_001, p_002] }
2. RELATE Event -> has_project -> proj_001
3. CREATE Task { title: "Prepare agenda", assignee: p_001 }
4. RELATE Task -> for_event -> event_001
5. CREATE Task { title: "Send summary", assignee: p_001, blockers: [task_001] }
```

Each step is validated before execution. Rollback on constraint violation.

## Integration Patterns

### With Causal Inference

Log ontology mutations as causal actions:

```python
# When creating/updating entities, also log to causal action log
action = {
    "action": "create_entity",
    "domain": "ontology", 
    "context": {"type": "Task", "project": "proj_001"},
    "outcome": "created"
}
```

### Cross-Skill Communication

```python
# Email skill creates commitment
commitment = ontology.create("Commitment", {
    "source_message": msg_id,
    "description": "Send report by Friday",
    "due": "2026-01-31"
})

# Task skill picks it up
tasks = ontology.query("Commitment", {"status": "pending"})
for c in tasks:
    ontology.create("Task", {
        "title": c.description,
        "due": c.due,
        "source": c.id
    })
```

## Quick Start

```bash
# Initialize ontology storage
mkdir -p memory/ontology
touch memory/ontology/graph.jsonl

# Create schema (optional but recommended)
python3 scripts/ontology.py schema-append --data '{
  "types": {
    "Task": { "required": ["title", "status"] },
    "Project": { "required": ["name"] },
    "Person": { "required": ["name"] }
  }
}'

# Start using
python3 scripts/ontology.py create --type Person --props '{"name":"Alice"}'
python3 scripts/ontology.py list --type Person
```

## References

- `references/schema.md` — Full type definitions and constraint patterns
- `references/queries.md` — Query language and traversal examples

## Instruction Scope

Runtime instructions operate on local files (`memory/ontology/graph.jsonl` and `memory/ontology/schema.yaml`) and provide CLI usage for create/query/relate/validate; this is within scope. The skill reads/writes workspace files and will create the `memory/ontology` directory when used. Validation includes property/enum/forbidden checks, relation type/cardinality validation, acyclicity for relations marked `acyclic: true`, and Event `end >= start` checks; other higher-level constraints may still be documentation-only unless implemented in code.
