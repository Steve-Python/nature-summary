# nature-summary

`nature-summary` is an end-to-end literature-review skill for Codex-style AI agents. It starts from a user-provided research direction, searches and downloads review papers, decomposes the topic into sub-directions, searches and downloads focused papers, classifies PDFs, generates translated paper readers, drafts a review manuscript, and builds a dynamic HTML preview site.

## Dependency

This skill depends on the `nature-skills` ecosystem by Yuan1z0825:

https://github.com/Yuan1z0825/nature-skills

Install `nature-skills` first. At minimum, the following skills must be available before using `nature-summary`:

- `nature-academic-search`
- `nature-downloader`
- `nature-reader`
- `nature-writing`

`nature-summary` is an orchestration skill: it calls and coordinates those skills rather than replacing them.

## Triggers

Use this skill when the user asks for:

- `综述`
- `调研`
- `nature summary`
- literature review / research survey
- turning a topic into categorized papers, translated readers, and a review manuscript

## What It Does

The workflow has six stages:

1. Search 5-10 open-access review papers for the user's topic with `nature-academic-search`, download them with `nature-downloader`, and read them to decompose the topic into sub-directions.
2. For each sub-direction, search 5-10 focused papers, list the literature, and download automatically through authorized browser access when possible. If automatic download is blocked, open the article pages for manual download.
3. After downloads are complete, classify and archive PDFs by direction.
4. Use `nature-reader` to read and translate the abstract and conclusion of each paper by default.
5. Use `nature-writing` to draft a review manuscript from all generated `paper.md` readers and the original PDFs.
6. Generate a dynamic static web preview with `scripts/build_reader.py`.

After the preview is built, the skill asks which directions deserve deeper attention. For selected directions, it reruns `nature-reader` in full-paper translation mode and replaces the coarse `paper.md` readers.

## Installation

### 1. Install `nature-skills` first

Install or clone Yuan1z0825's `nature-skills` into your AI agent's skill directory according to your agent's skill-loading rules.

Typical Codex location on Windows:

```powershell
$skillRoot = "$env:USERPROFILE\.codex\skills"
New-Item -ItemType Directory -Force -Path $skillRoot | Out-Null
```

Then make sure the dependency skills exist under that root, for example:

```text
%USERPROFILE%\.codex\skills\nature-academic-search
%USERPROFILE%\.codex\skills\nature-downloader
%USERPROFILE%\.codex\skills\nature-reader
%USERPROFILE%\.codex\skills\nature-writing
```

### 2. Install `nature-summary`

Copy this folder into the same skill root:

```powershell
$skillRoot = "$env:USERPROFILE\.codex\skills"
Copy-Item -Recurse -Force ".\nature-summary" "$skillRoot\nature-summary"
```

If your agent uses another skill directory, copy `nature-summary` there instead.

### 3. Verify

Confirm the skill folder contains:

```text
nature-summary/
  SKILL.md
  README.md
  agents/openai.yaml
  references/workflow.md
  references/web-preview-template.html
  scripts/build_reader.py
```

The web preview generator can be checked with:

```powershell
python .\nature-summary\scripts\build_reader.py --project "<review-project-folder>" --dry-run
```

## Quick Install Prompt For Codex Or Other AI Agents

Send this prompt to Codex or another AI coding agent:

```text
Install the `nature-summary` skill. First make sure Yuan1z0825/nature-skills is installed and that `nature-academic-search`, `nature-downloader`, `nature-reader`, and `nature-writing` are available in the active skill directory. Then copy this `nature-summary` folder into the same skill root, preserving `SKILL.md`, `README.md`, `agents/`, `references/`, and `scripts/`. After installation, run `python nature-summary/scripts/build_reader.py --project "<review-project-folder>" --dry-run` to verify the bundled preview generator.
```

Chinese version:

```text
请安装 `nature-summary` skill。安装前先确认已经安装 Yuan1z0825/nature-skills，并且当前 skill 目录中已有 `nature-academic-search`、`nature-downloader`、`nature-reader`、`nature-writing`。然后把整个 `nature-summary` 文件夹复制到同一个 skill 根目录，保留 `SKILL.md`、`README.md`、`agents/`、`references/`、`scripts/`。安装完成后运行 `python nature-summary/scripts/build_reader.py --project "<综述项目文件夹>" --dry-run` 检查网页生成器是否可用。
```

## Preview Generator

`scripts/build_reader.py` scans a review project folder and generates:

```text
index.html
reader.html
preview.html
```

Usage:

```powershell
python .\nature-summary\scripts\build_reader.py --project "<review-project-folder>"
```

The generated pages are static and backend-free. They embed Markdown and CSV data into local HTML, so the user can open `index.html` directly or serve the folder locally.

## Access And Ethics

Use only legitimate open-access or institution-authorized full text. Do not bypass paywalls, CAPTCHA, DRM, Cloudflare, publisher bot checks, or institutional authentication. If automatic download is blocked, open the article pages for the user and wait for manual download.

