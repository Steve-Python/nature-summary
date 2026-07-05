---
name: nature-summary
description: >-
  End-to-end Nature-style literature-review workflow for a user-provided
  research direction: open-access review search, authorized downloading,
  direction decomposition, focused literature search, classification,
  abstract/conclusion translation, review-paper drafting, and dynamic web
  preview. Use when the user asks for a 综述, 调研, literature review, research
  survey, "nature summary", or wants to turn a topic into categorized papers,
  translated readers, and a review manuscript.
---

# Nature Summary

Use this skill to turn a research direction into a complete literature-review
project. Coordinate the existing `nature-academic-search`, `nature-downloader`,
`nature-reader`, and `nature-writing` skills rather than replacing them.

## Installation Guidance For Agents

When asked to install this skill from
`https://github.com/Steve-Python/nature-summary`, first ensure that
`Yuan1z0825/nature-skills` dependencies are installed in the same active skill
root.

Before installing those dependencies, ask the user to choose one dependency
mode unless they already specified it:

1. `minimal`: install `_shared` plus only the four required companion skills:
   `nature-academic-search`, `nature-downloader`, `nature-reader`, and
   `nature-writing`.
2. `full`: install the complete `skills/` directory from
   `Yuan1z0825/nature-skills`, including `_shared`.

In both modes, preserve complete skill directories. Do not install only
`SKILL.md`; Nature skills may depend on `references/`, `static/`,
`manifest.yaml`, scripts, assets, or `../_shared`.

After dependencies are present, copy the full `nature-summary` directory into
the same skill root and preserve:

```text
SKILL.md
README.md
agents/
references/
scripts/
```

Use `scripts/install_codex.ps1` when running from this repository on Windows:

```powershell
.\scripts\install_codex.ps1 -DependencyMode minimal
.\scripts\install_codex.ps1 -DependencyMode full
.\scripts\install_codex.ps1 -Check
```

Restart Codex after installing or updating skills.

## Required Companion Skills

Invoke companion skills in this order:

1. `nature-academic-search` for search strategy, multi-source retrieval,
   metadata export, and citation cleanup.
2. `nature-downloader` for legitimate open-access or institution-authorized
   downloading through the user's logged-in browser.
3. `nature-reader` for paper-level reading files. In the default pass, read and
   translate abstracts and conclusions only.
4. `nature-writing` for drafting the final review manuscript from the generated
   readers and the original papers.

Respect the access boundaries from `nature-downloader`: do not bypass paywalls,
CAPTCHA, publisher bot checks, DRM, or institutional login flows. If automatic
download is blocked, open the paper pages in the user's browser and wait for
the user to download them.

## Project Contract

Create one project folder for each review task. Use a clear title such as:

```text
<topic>_literature_review/
  metadata/
  PDFs/
  readers/
  draft/
  archive/
  logs/
```

Keep a manifest in `metadata/` throughout the workflow. Include at least `id`,
`direction`, `title`, `year`, `venue`, `doi`, `url`, `download_status`,
`pdf_path`, `reader_path`, and `notes`.

## Six-Step Workflow

### 1. Seed With Open-Access Reviews

Use `nature-academic-search` to search for 5-10 open-access review articles
matching the user's direction. Prefer recent reviews, highly cited reviews, and
reviews that explicitly map mechanisms, applications, or methods.

Use `nature-downloader` to download the review articles through legitimate
open-access sources first. If a review is institution-authorized but not open
access, use the user's authenticated browser only when permitted.

Read these seed reviews enough to decompose the user's broad problem into
several directions. Save the direction map to:

```text
metadata/direction_map.md
metadata/seed_reviews.csv
```

### 2. Search Each Direction

For each direction, use `nature-academic-search` to retrieve 5-10 relevant
papers. Build a literature list before downloading, and show it to the user
when the choice of papers is uncertain or the batch is large.

Use `nature-downloader` to download papers automatically when browser control
and authorized access are available. If direct download is not possible, open
the paper pages in the user's browser and ask the user to download them
manually. Record these papers as `manual_download_waiting_user`.

### 3. Wait, Then Classify And Archive

After the user says downloads are complete, inventory the download folder and
classify every file by direction. Move or copy files into:

```text
PDFs/<direction-id>/
archive/manual_downloads/
```

Update the manifest with final file paths and statuses. Do not overwrite
user-downloaded PDFs unless a duplicate is confirmed.

### 4. Coarse Read And Translate

For each paper, use `nature-reader` to create a `paper.md` reader focused on:

- metadata and citation information.
- the abstract, translated into Chinese.
- the conclusion or final discussion section, translated into Chinese.
- a short "why it matters for the review topic" note.

This default pass is intentionally a coarse read. Do not claim full-paper
translation unless step 6's optional deep-reading pass is requested.

### 5. Draft The Review

Use all generated `paper.md` files, the manifest, direction map, and the
original PDFs as evidence. Then use `nature-writing` to draft a review
manuscript titled around the user's original direction.

Save outputs in `draft/`:

```text
draft/review.md
draft/review_outline.md
draft/evidence_gap_table.md
```

The review must distinguish review evidence, original research evidence,
unresolved gaps, and claims requiring more support.

### 6. Build The Dynamic Preview Website

Use `scripts/build_reader.py` from this skill to generate a web preview:

```powershell
python <skill-root>\nature-summary\scripts\build_reader.py --project "<project-folder>"
```

The script scans `readers/**/paper.md`, `draft/*.md`, and
`metadata/*.csv/*.md`, then writes:

```text
index.html
reader.html
preview.html
```

The web preview template is documented in
`references/web-preview-template.html`.

## Final User Checkpoint

After building the preview site and review draft, ask:

```text
你对哪些方向额外感兴趣，需要我进一步做全文精读翻译？
```

If the user chooses one or more directions, use `nature-reader` for full-paper
translation of those direction's papers. Replace the coarse `paper.md` files
with the full readers, preserve the old coarse readers under
`archive/coarse_readers/`, rebuild the preview website, and update the review
if the new evidence changes the argument.

## References

Read these only when needed:

- `references/workflow.md` for detailed execution rules, manifests, statuses,
  and checkpoints.
- `references/web-preview-template.html` for the expected generated website
  layout.
