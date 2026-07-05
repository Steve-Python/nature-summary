# nature-summary

`nature-summary` is an end-to-end literature-review skill for Codex-style AI
agents. It starts from a user-provided research direction, searches and
downloads review papers, decomposes the topic into sub-directions, searches and
downloads focused papers, classifies PDFs, generates translated paper readers,
drafts a review manuscript, and builds a dynamic HTML preview site.

## Dependency

This skill depends on the `nature-skills` ecosystem by Yuan1z0825:

https://github.com/Yuan1z0825/nature-skills

Before installing dependencies, choose one of two modes:

| Mode | What gets installed | When to choose it |
| --- | --- | --- |
| `minimal` | `_shared` plus `nature-academic-search`, `nature-downloader`, `nature-reader`, and `nature-writing` | You only want the dependencies required by `nature-summary`. |
| `full` | Every top-level directory under `Yuan1z0825/nature-skills/skills/`, including `_shared` | You want the complete Nature Skills ecosystem available in Codex. |

`_shared` is installed in both modes because some Nature skills reference shared
materials outside their own folder. Keep the full folder structure; do not copy
only `SKILL.md`.

`nature-summary` is an orchestration skill: it calls and coordinates companion
skills rather than replacing them.

## Triggers

Use this skill when the user asks for:

- `综述`
- `调研`
- `nature summary`
- literature review / research survey
- turning a topic into categorized papers, translated readers, and a review manuscript

## What It Does

The workflow has six stages:

1. Search 5-10 open-access review papers for the user's topic with
   `nature-academic-search`, download them with `nature-downloader`, and read
   them to decompose the topic into sub-directions.
2. For each sub-direction, search 5-10 focused papers, list the literature, and
   download automatically through authorized browser access when possible. If
   automatic download is blocked, open the article pages for manual download.
3. After downloads are complete, classify and archive PDFs by direction.
4. Use `nature-reader` to read and translate the abstract and conclusion of each
   paper by default.
5. Use `nature-writing` to draft a review manuscript from all generated
   `paper.md` readers and the original PDFs.
6. Generate a dynamic static web preview with `scripts/build_reader.py`.

After the preview is built, the skill asks which directions deserve deeper
attention. For selected directions, it reruns `nature-reader` in full-paper
translation mode and replaces the coarse `paper.md` readers.

## Recommended Codex Install Prompt

Send this prompt to Codex or another AI coding agent:

```text
Install the `nature-summary` skill from https://github.com/Steve-Python/nature-summary.

Before installing dependencies, ask me to choose one dependency mode:
1. `minimal`: install only `_shared` plus `nature-academic-search`, `nature-downloader`, `nature-reader`, and `nature-writing` from https://github.com/Yuan1z0825/nature-skills.
2. `full`: install the complete `skills/` directory from https://github.com/Yuan1z0825/nature-skills, including `_shared`.

Then copy the full `nature-summary` folder into the same Codex skill root, preserving `SKILL.md`, `README.md`, `agents/`, `references/`, and `scripts/`. Do not copy only `SKILL.md`.

After installation, run:
python nature-summary/scripts/build_reader.py --project "<review-project-folder>" --dry-run
to verify the bundled preview generator.
```

Chinese version:

```text
请从 https://github.com/Steve-Python/nature-summary 安装 `nature-summary` skill。

安装依赖前，请先让我选择一种依赖安装模式：
1. `minimal`：只从 https://github.com/Yuan1z0825/nature-skills 安装 `_shared` 以及四个必需依赖 skill：`nature-academic-search`、`nature-downloader`、`nature-reader`、`nature-writing`。
2. `full`：从 https://github.com/Yuan1z0825/nature-skills 安装完整的 `skills/` 目录，包括 `_shared`。

然后把完整的 `nature-summary` 文件夹复制到同一个 Codex skill root，保留 `SKILL.md`、`README.md`、`agents/`、`references/`、`scripts/`，不要只复制 `SKILL.md`。

安装后运行：
python nature-summary/scripts/build_reader.py --project "<综述项目文件夹>" --dry-run
验证内置网页预览生成器。
```

## PowerShell Installer

From a checkout of this repository:

```powershell
.\scripts\install_codex.ps1
```

The script prompts for the dependency mode. You can also choose explicitly:

```powershell
.\scripts\install_codex.ps1 -DependencyMode minimal
.\scripts\install_codex.ps1 -DependencyMode full
```

If PowerShell blocks local scripts, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_codex.ps1 -DependencyMode minimal
```

Verify an existing install:

```powershell
.\scripts\install_codex.ps1 -Check
```

By default, the destination is:

```text
%USERPROFILE%\.codex\skills
```

You can override it with either `-SkillRoot` or `CODEX_SKILLS_DIR`.

## Manual Installation

### 1. Choose dependency mode

For `minimal`, copy these directories from `Yuan1z0825/nature-skills/skills/`
into your Codex skill root:

```text
_shared/
nature-academic-search/
nature-downloader/
nature-reader/
nature-writing/
```

For `full`, copy every top-level directory under
`Yuan1z0825/nature-skills/skills/` into the Codex skill root.

### 2. Install `nature-summary`

Copy this repository folder into the same skill root:

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

Restart Codex after installing or updating skills so the new skill set is
loaded.

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

The generated pages are static and backend-free. They embed Markdown and CSV
data into local HTML, so the user can open `index.html` directly or serve the
folder locally.

## Access And Ethics

Use only legitimate open-access or institution-authorized full text. Do not
bypass paywalls, CAPTCHA, DRM, Cloudflare, publisher bot checks, or
institutional authentication. If automatic download is blocked, open the article
pages for the user and wait for manual download.
