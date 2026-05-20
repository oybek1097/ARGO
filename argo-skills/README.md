# ARGO Skills Catalogue

This directory is the **bundled seed catalogue** of skills for the ARGO Agent
hub (Technical Specification §4.7, Sprint 11). It ships inside the ARGO repo
as the lowest-priority — but always-present — skill tap, alongside
`~/.argo/skills/` (user skills) and the remote `skills.argo-agent.io` hub.

## What is a skill?

A skill is a single Markdown file in the
[agentskills.io](https://agentskills.io)-compatible format: a `--- ... ---`
YAML-style frontmatter block followed by a focused, numbered procedure the
agent follows when the skill's triggers match the user's request.

```markdown
---
name: Deploy to Kubernetes
slug: deploy-k8s
trigger: deploy, kubernetes, k8s, helm
category: devops
quality: 0.88
author: argo-team
license: MIT
requires_tools: [kubectl, helm_install, vault_get]
---

# Deploy to Kubernetes

1. ...
```

### Frontmatter fields

| Field            | Meaning                                                       |
|------------------|---------------------------------------------------------------|
| `name`           | Human-readable skill name.                                    |
| `slug`           | Unique, kebab-case identifier (also the file name).           |
| `trigger`        | Comma-separated keywords that activate the skill.             |
| `category`       | One of the category directories below.                        |
| `quality`        | Curator quality score in `[0, 1]` (see §4.7 curator pipeline).|
| `author`         | Always `argo-team` for bundled skills.                        |
| `license`        | `MIT` for the whole bundled catalogue.                        |
| `requires_tools` | Tools the procedure expects to be available.                  |

The `SkillLoader` (`argo_brain/skills/loader.py`) parses these files without a
YAML dependency.

## Organisation

Skills are grouped into ten category subdirectories:

| Category        | Focus                                                         |
|-----------------|---------------------------------------------------------------|
| `devops/`       | Deployment, CI/CD, infrastructure, observability.             |
| `coding/`       | Writing, reviewing, testing and refactoring code.             |
| `data/`         | Data cleaning, SQL, ETL, analysis and ML basics.              |
| `web/`          | Frontend, web APIs, scraping, performance and accessibility.  |
| `communication/`| Emails, summaries, docs and stakeholder messaging.            |
| `system/`       | Linux administration, networking and reliability.            |
| `security/`     | Hardening, auditing, secrets and incident response.           |
| `productivity/` | Planning, prioritisation and team process.                    |
| `central-asia/` | Uzbek / CIS-specific: Yandex Cloud, Payme, Click, uz/ru docs. |
| `general/`      | Cross-cutting reasoning, research and writing skills.         |

## Seeding the hub

`scripts/seed-hub.py` walks this directory, builds a signed `.argopkg` for
each skill and publishes it into a `HubRegistry`. See `argo-plugins/README.md`
for the plugin half of the catalogue.

Run the bundled catalogue test from the `argo-brain/` directory:

```sh
cd argo-brain && python3 -m unittest tests.test_seed_catalogue -v
```
