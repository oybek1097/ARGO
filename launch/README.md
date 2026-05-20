# ARGO Agent v3.0 — Launch Materials

This directory holds everything needed for the ARGO v3.0 GA launch:
community posts, a press kit, and tutorial video scripts.

ARGO is an open-source, multilingual AI agent platform — a Rust gateway
(`argo-core`) plus a Python brain (`argo-brain`). It is optimized for
Central Asian languages (Uzbek, Russian, Kazakh, Kyrgyz, Tajik) and for
DevOps, and it is self-hosted first. MIT licensed.

> Status note: ARGO is **alpha approaching GA**. All launch copy is
> written honestly — it describes what works today and is candid about
> what is still on the roadmap. Do not add overclaiming marketing
> language ("100,000x faster", etc.); the technical spec explicitly
> disowns that style.

---

## Index of materials

| File | Purpose |
|---|---|
| `README.md` | This index + launch-day runbook (you are here) |
| `product-hunt.md` | Product Hunt launch post — tagline, description, maker's first comment, gallery shot list, topics |
| `hacker-news.md` | "Show HN" post — title, body, anticipated FAQ |
| `reddit-localllama.md` | r/LocalLLaMA post — self-hosting / local models / privacy angle |
| `press-kit.md` | Press kit — descriptions, key facts, quote, asset list, contacts, links |
| `tutorials/` | 12 tutorial video scripts (4 topics × 3 languages: EN/RU/UZ) |
| `tutorials/README.md` | Index of the 12 tutorial scripts |

---

## Launch-day runbook

All times in the runbook are relative to **T = launch hour**. Product Hunt
launches reset at 00:01 PT, so pick the calendar date accordingly.

### T minus 1 week

- [ ] Freeze the `main` branch for the GA tag; cut a release branch.
- [ ] Verify the README quick start works on a clean machine (Linux + macOS).
- [ ] Confirm `python3 -m argo_brain selftest` and `doctor` pass.
- [ ] Confirm `docker compose up` builds and `/api/health` returns OK.
- [ ] Record the 4 core tutorial videos from the scripts in `tutorials/`
      (EN first; RU/UZ voice-overs can follow within the launch week).
- [ ] Upload videos (unlisted) to YouTube; collect the links.
- [ ] Prepare gallery images per the shot list in `product-hunt.md`.
- [ ] Draft a `v3.0.0` GitHub release with changelog highlights.
- [ ] Line up 3-5 contributors/early users who can comment honestly.

### T minus 1 day

- [ ] Tag and publish the `v3.0.0` GitHub release (keep the page ready).
- [ ] Schedule the Product Hunt post for 00:01 PT.
- [ ] Pre-write the HN and Reddit posts; do not submit yet.
- [ ] Pin a GA announcement issue/discussion in the repo.
- [ ] Double-check all links in every post resolve (no 404s).

### T = launch hour

- [ ] Product Hunt post goes live; immediately add the maker's first
      comment (`product-hunt.md`).
- [ ] Submit the "Show HN" post (`hacker-news.md`) — best mid-morning ET
      on a weekday.
- [ ] Submit the r/LocalLLaMA post (`reddit-localllama.md`).
- [ ] Send the press kit (`press-kit.md`) to the contact list.
- [ ] Post the announcement on the project's social channels.

### T plus 0 to 8 hours (active window)

- [ ] Answer every comment on PH / HN / Reddit. Be honest about alpha
      status and the roadmap. Never argue; thank people for bug reports.
- [ ] Triage incoming GitHub issues; label `launch-feedback`.
- [ ] Watch the repo CI and the hosted demo for load problems.
- [ ] Note recurring questions — fold good ones back into the FAQ.

### T plus 1 day

- [ ] Post a short thank-you / metrics update on the launch threads.
- [ ] File issues for every actionable piece of feedback.
- [ ] Update `tutorials/` or docs if a question revealed a gap.

### Success criteria (from the executive summary, 3 months post-launch)

- ≥ 1,000 GitHub stars
- ≥ 50 contributors
- ≥ 10 published skills
- ≥ 5 enterprise pilot deployments (UZ/RU/KZ)
- No open P0 security findings
- 26+ languages validated by real users

---

## Tone checklist (apply to every post)

- Honest: ARGO is alpha approaching GA — say so.
- Specific: cite real, current facts (84 tests passing, 13 built-in
  tools, Python stdlib only, MIT, Rust core).
- No hype multipliers in marketing copy. Performance targets from the
  spec are *targets* — label them as such.
- Lead with the real differentiators: self-hosted/sovereign, Central
  Asian languages, DevOps, and "easy to try" (no API key, no install).
