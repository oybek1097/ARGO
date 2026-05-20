# Skills

A **skill** is a reusable chunk of instructions, written in Markdown, that
ARGO can inject into the system prompt when a conversation is relevant to it.
Skills let you teach ARGO domain knowledge or a standard procedure without
touching code.

ARGO's skill format is **compatible with [agentskills.io](https://agentskills.io)**:
a `.md` file with a small YAML-style frontmatter header.

## Skill file format

A skill is a single Markdown file. The frontmatter block (between two `---`
lines) carries the metadata; the body is the instruction text.

```markdown
---
name: deploy-k8s
trigger: deploy, kubernetes, k8s
category: devops
---
# Deploy to Kubernetes

When the user asks to deploy a service:

1. Confirm the target cluster and namespace.
2. Validate the manifest with `kubectl apply --dry-run=server`.
3. Apply the manifest and watch the rollout.
4. Report the rollout status back to the user.
```

### Frontmatter fields

| Field | Required | Meaning |
|---|---|---|
| `name` | yes | Human-readable skill name. |
| `slug` | no | Stable identifier; defaults to `name`, then to the filename. |
| `trigger` | no | Comma-separated keywords. The skill activates when one occurs in the user's message. |
| `category` | no | A grouping label (default `general`). |

The frontmatter is parsed by ARGO's own stdlib parser — no YAML dependency is
required. Anything after the closing `---` is the skill body.

## Where skills live

Skill files are loaded from `~/.argo/skills/` (created by the setup wizard).
Drop `.md` files into that directory and they are picked up on the next load.

## How skills are selected

**Module:** `argo_brain/skills/loader.py`

The `SkillLoader` scans the skill directory and parses every `*.md` file into
a `Skill` object. During the agent loop:

1. The incoming user message is matched against every skill's `trigger`
   keywords (case-insensitive substring match).
2. Up to a small number of matching skills (default 3) are selected as
   *relevant*.
3. Their bodies are injected into the system prompt for that request.

A skill with no triggers never activates automatically — it can still be
referenced by slug. Skills are matched on keywords, not semantics; choose
trigger words that genuinely appear in user requests.

## The skill curator

**Module:** `argo_brain/skills/curator.py`

As a skill library grows, some skills become stale, unused or
near-duplicates. The **`SkillCurator`** is an autonomous quality pipeline that
grades skills against their real usage history and recommends what to keep,
archive or send for human review.

### Grading

`SkillCurator.grade()` produces a `0.0–1.0` quality score for a skill by
blending three signals:

| Signal | Weight | Meaning |
|---|---|---|
| Success rate | 0.5 | Successful invocations ÷ total recorded outcomes (neutral 0.5 with no history). |
| Frequency | 0.3 | How often the skill is used, with diminishing returns past ~10 uses. |
| Recency | 0.2 | Exponential decay on days since last use (half-life 30 days by default). |

Success rate is weighted highest because a skill that fails is actively
harmful.

### Duplicate detection

`find_duplicates()` compares every pair of skills with
`difflib.SequenceMatcher` and reports pairs whose textual overlap is at or
above the `duplicate_threshold` (default `0.8`).

### Recommendations

`recommend()` sorts every skill into one of three buckets:

- **keep** — grade at or above `keep_grade` (default `0.6`).
- **archive** — grade below `archive_grade` (default `0.3`) *and* the skill
  has zero recorded uses.
- **review** — everything else, including low-grade skills that are still in
  use and therefore need a human decision.

### Running the full pipeline

`SkillCurator.run(skills, stats)` returns a complete report:

```python
from argo_brain.skills.curator import SkillCurator

curator = SkillCurator()
report = curator.run(skills, stats)
# report = {
#   "total": <int>,
#   "grades": {slug: score, ...},
#   "duplicates": [(slug_a, slug_b), ...],
#   "recommendations": {"keep": [...], "archive": [...], "review": [...]},
# }
```

`stats` is a mapping of skill slug to a dict with `use_count`,
`success_count`, `failure_count` and `age_days`. The curator is otherwise
stateless — usage statistics are supplied externally.

## Sharing skills

Skills can be packaged and distributed through the ARGO Hub as signed
`.argopkg` packages. See [Hub & Marketplace](hub.md).

## See also

- [Hub & Marketplace](hub.md) — publishing and installing skills.
- [Tools](tools.md) — skills describe *what to do*; tools are *how* ARGO acts.
- [Configuration](configuration.md) — the `~/.argo/skills/` directory.
