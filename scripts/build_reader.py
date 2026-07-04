#!/usr/bin/env python3
"""Build a static literature-review preview site.

The script expects a nature-summary project folder and writes:
index.html, reader.html, preview.html.

It uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


TEXT_EXTENSIONS = {".md", ".markdown", ".txt"}


@dataclass
class Paper:
    id: str
    title: str
    direction: str
    year: str
    venue: str
    doi: str
    reader_path: Path
    pdf_path: Path | None
    html: str
    preview: str


def read_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def json_for_script(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return (
        raw.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def slug(value: str, fallback: str = "item") -> str:
    value = re.sub(r"\s+", "-", value.strip().lower())
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    value = value.strip("-._")
    return value or fallback


def norm_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def pick(row: dict[str, str], *names: str) -> str:
    normalized = {norm_key(k): v for k, v in row.items()}
    for name in names:
        value = normalized.get(norm_key(name), "")
        if value:
            return str(value).strip()
    return ""


def first_heading(markdown: str) -> str:
    for line in markdown.splitlines():
        match = re.match(r"^\s{0,3}#\s+(.+?)\s*$", line)
        if match:
            return re.sub(r"[*_`]+", "", match.group(1)).strip()
    for line in markdown.splitlines():
        text = line.strip()
        if text:
            return re.sub(r"[*_`]+", "", text)[:120]
    return "Untitled paper"


def markdown_preview(markdown: str, limit: int = 260) -> str:
    text = re.sub(r"```.*?```", " ", markdown, flags=re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[#>*_`|[\]()-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit] + ("..." if len(text) > limit else "")


def inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        escaped,
    )
    return escaped


def is_table_separator(line: str) -> bool:
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def render_markdown_table(lines: list[str]) -> str:
    rows = []
    for line in lines:
        rows.append([inline_markdown(cell.strip()) for cell in line.strip().strip("|").split("|")])
    if len(rows) < 2:
        return ""
    header = rows[0]
    body = rows[2:] if is_table_separator(lines[1]) else rows[1:]
    out = ["<div class=\"table-wrap\"><table><thead><tr>"]
    out.extend(f"<th>{cell}</th>" for cell in header)
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>")
        out.extend(f"<td>{cell}</td>" for cell in row)
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def markdown_to_html(markdown: str) -> str:
    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    paragraph: list[str] = []
    in_code = False
    code_lines: list[str] = []
    i = 0

    def flush_paragraph() -> None:
        if paragraph:
            out.append(f"<p>{inline_markdown(' '.join(paragraph).strip())}</p>")
            paragraph.clear()

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines.clear()
                in_code = False
            else:
                flush_paragraph()
                in_code = True
            i += 1
            continue
        if in_code:
            code_lines.append(line)
            i += 1
            continue
        if not stripped:
            flush_paragraph()
            i += 1
            continue
        if "|" in stripped and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            flush_paragraph()
            table_lines = [line, lines[i + 1]]
            i += 2
            while i < len(lines) and "|" in lines[i].strip():
                table_lines.append(lines[i])
                i += 1
            out.append(render_markdown_table(table_lines))
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            level = min(len(heading.group(1)), 4)
            out.append(f"<h{level}>{inline_markdown(heading.group(2))}</h{level}>")
            i += 1
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            block = [stripped.lstrip("> ").strip()]
            i += 1
            while i < len(lines) and lines[i].strip().startswith(">"):
                block.append(lines[i].strip().lstrip("> ").strip())
                i += 1
            out.append(f"<blockquote>{inline_markdown(' '.join(block))}</blockquote>")
            continue
        if re.match(r"^[-*+]\s+", stripped):
            flush_paragraph()
            items = []
            while i < len(lines) and re.match(r"^[-*+]\s+", lines[i].strip()):
                item = re.sub(r"^[-*+]\s+", "", lines[i].strip())
                items.append(f"<li>{inline_markdown(item)}</li>")
                i += 1
            out.append("<ul>" + "".join(items) + "</ul>")
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            flush_paragraph()
            items = []
            while i < len(lines) and re.match(r"^\d+[.)]\s+", lines[i].strip()):
                item = re.sub(r"^\d+[.)]\s+", "", lines[i].strip())
                items.append(f"<li>{inline_markdown(item)}</li>")
                i += 1
            out.append("<ol>" + "".join(items) + "</ol>")
            continue
        if stripped in {"---", "***", "___"}:
            flush_paragraph()
            out.append("<hr>")
            i += 1
            continue
        paragraph.append(stripped)
        i += 1
    flush_paragraph()
    if in_code:
        out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    return "\n".join(out)


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    text = read_text(path)
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.DictReader(text.splitlines(), dialect=dialect))
    return [{k or "column": (v or "") for k, v in row.items()} for row in rows]


def csv_to_html(path: Path) -> tuple[str, int, int]:
    rows = read_csv_rows(path)
    if not rows:
        return "<p>Empty table.</p>", 0, 0
    headers = list(rows[0].keys())
    out = ["<div class=\"table-wrap data-table-wrap\"><table class=\"data-table\"><thead><tr>"]
    out.extend(f"<th>{html.escape(header)}</th>" for header in headers)
    out.append("</tr></thead><tbody>")
    for row in rows:
        out.append("<tr>")
        out.extend(f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers)
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out), len(rows), len(headers)


def load_metadata(project: Path) -> dict[str, dict[str, str]]:
    metadata: dict[str, dict[str, str]] = {}
    metadata_dir = project / "metadata"
    if not metadata_dir.exists():
        return metadata
    for path in sorted(metadata_dir.glob("*.csv")):
        try:
            rows = read_csv_rows(path)
        except Exception:
            continue
        for row in rows:
            paper_id = pick(row, "id", "paper_id", "文献编号", "编号")
            if not paper_id:
                continue
            current = metadata.setdefault(paper_id, {})
            for key, value in row.items():
                if value and not current.get(key):
                    current[key] = value
    return metadata


def paper_id_from_path(path: Path, used: set[str]) -> str:
    parent = path.parent.name
    if parent.lower() in {"reader", "readers"}:
        parent = path.stem
    candidate = parent
    if candidate.lower().startswith("manual") and len(path.parents) > 1:
        candidate = path.parent.name
    candidate = slug(candidate, "paper").upper()
    base = candidate
    index = 2
    while candidate in used:
        candidate = f"{base}-{index}"
        index += 1
    used.add(candidate)
    return candidate


def find_pdf(project: Path, paper_id: str, info: dict[str, str]) -> Path | None:
    explicit = pick(info, "pdf_path", "pdf", "file", "文件路径")
    if explicit:
        candidate = Path(explicit)
        if not candidate.is_absolute():
            candidate = project / candidate
        if candidate.exists():
            return candidate
    pdf_root = project / "PDFs"
    if not pdf_root.exists():
        return None
    lower_id = paper_id.lower()
    for path in sorted(pdf_root.rglob("*.pdf")):
        if lower_id in path.name.lower():
            return path
    return None


def collect_reader_paths(project: Path) -> list[Path]:
    readers = project / "readers"
    if not readers.exists():
        return []
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in ("**/paper.md", "**/reader.md"):
        for path in sorted(readers.glob(pattern)):
            resolved = path.resolve()
            if resolved not in seen:
                paths.append(path)
                seen.add(resolved)
    return paths


def collect_papers(project: Path) -> list[Paper]:
    metadata = load_metadata(project)
    used: set[str] = set()
    papers: list[Paper] = []
    for path in collect_reader_paths(project):
        paper_id = paper_id_from_path(path, used)
        text = read_text(path)
        info = metadata.get(paper_id, {})
        title = pick(info, "title", "题名", "文献题名") or first_heading(text)
        direction = pick(info, "direction", "direction_name", "category", "类别", "方向") or "Unclassified"
        year = pick(info, "year", "年份")
        venue = pick(info, "venue", "journal", "source", "期刊")
        doi = pick(info, "doi")
        papers.append(
            Paper(
                id=paper_id,
                title=title,
                direction=direction,
                year=year,
                venue=venue,
                doi=doi,
                reader_path=path,
                pdf_path=find_pdf(project, paper_id, info),
                html=markdown_to_html(text),
                preview=markdown_preview(text),
            )
        )
    return papers


def collect_preview_docs(project: Path) -> list[dict[str, object]]:
    docs: list[dict[str, object]] = []
    candidates: list[Path] = []
    for folder in ("draft", "metadata"):
        root = project / folder
        if root.exists():
            candidates.extend(sorted(root.glob("*.md")))
            candidates.extend(sorted(root.glob("*.csv")))
    for path in candidates:
        if path.suffix.lower() == ".csv":
            try:
                rendered, rows, cols = csv_to_html(path)
            except Exception as exc:
                rendered, rows, cols = f"<p>Could not render CSV: {html.escape(str(exc))}</p>", 0, 0
            kind = "csv"
        elif path.suffix.lower() in TEXT_EXTENSIONS:
            text = read_text(path)
            rendered = markdown_to_html(text)
            rows = text.count("\n") + 1 if text else 0
            cols = 0
            kind = "markdown"
        else:
            continue
        rel = path.relative_to(project).as_posix() if path.is_relative_to(project) else path.name
        docs.append(
            {
                "id": slug(path.stem),
                "title": path.stem.replace("_", " "),
                "description": rel,
                "kind": kind,
                "html": rendered,
                "rowCount": rows,
                "colCount": cols,
                "source": path.resolve().as_uri(),
            }
        )
    return docs


def as_link(path: Path | None) -> str:
    if not path:
        return ""
    try:
        return path.resolve().as_uri()
    except ValueError:
        return ""


COMMON_STYLE = r"""
:root {
  color-scheme: light;
  --bg: #f5f6f2;
  --panel: #ffffff;
  --ink: #18211f;
  --muted: #65716c;
  --line: #dce2dc;
  --accent: #286f6a;
  --accent-soft: #e8f2ee;
  --code: #f0f3f1;
  --shadow: 0 14px 34px rgba(35,45,42,0.08);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  min-height: 100vh;
  background: var(--bg);
  color: var(--ink);
  font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.65;
}
a { color: var(--accent); text-decoration: none; }
button, input { font: inherit; }
.app {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
}
.app.preview { grid-template-columns: 300px minmax(0, 1fr); }
.app.table-mode { height: 100vh; overflow: hidden; }
aside {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
  padding: 18px;
  border-right: 1px solid var(--line);
  background: #fbfcfa;
}
main { min-width: 0; width: 100%; padding: 22px 30px 42px; }
.preview-main.table-mode {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 12px 18px;
}
.brand { display: grid; gap: 9px; margin-bottom: 16px; }
.brand h1 { margin: 0; font-size: 22px; line-height: 1.2; letter-spacing: 0; }
.button, .brand a, .tool-link, .nav-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  color: var(--accent);
  padding: 7px 10px;
  font-weight: 700;
  cursor: pointer;
}
.button:hover, .brand a:hover, .tool-link:hover, .nav-button:hover {
  background: var(--accent-soft);
  border-color: var(--accent);
}
.search {
  width: 100%;
  min-height: 42px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 11px;
  margin-bottom: 14px;
  background: #fff;
  outline: none;
}
.search:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(40,111,106,0.14); }
.list { display: grid; gap: 8px; }
.list-button {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  padding: 10px;
  cursor: pointer;
  text-align: left;
  display: grid;
  gap: 4px;
}
.list-button.active { border-color: var(--accent); background: var(--accent-soft); }
.item-id { font-size: 12px; font-weight: 800; color: var(--accent); }
.item-title { color: var(--ink); font-size: 13px; line-height: 1.35; }
.item-meta, .meta-line { color: var(--muted); font-size: 13px; }
.reader-head, .preview-head, .markdown-body, .preview-body {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
  margin-left: auto;
  margin-right: auto;
}
.reader-head, .preview-head {
  padding: 18px 20px;
  margin-bottom: 16px;
  width: min(100%, 1440px);
  display: grid;
  gap: 10px;
}
.preview-main.table-mode .preview-head {
  flex: 0 0 auto;
  width: 80%;
  max-width: none;
  min-height: 44px;
  margin-bottom: 8px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.reader-head h2, .preview-head h2 {
  margin: 0;
  font-size: 24px;
  line-height: 1.25;
  letter-spacing: 0;
}
.preview-main.table-mode .preview-head h2 {
  flex: 1 1 auto;
  min-width: 0;
  font-size: 17px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-main.table-mode .preview-head .meta-line {
  flex: 0 1 auto;
  min-width: 0;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.preview-main.table-mode #docDescription,
.preview-main.table-mode .preview-head .tool-row { display: none; }
.tool-row, .nav-row, .reader-layout-tools { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.nav-row { margin-left: auto; }
.markdown-body, .preview-body {
  width: min(100%, 1440px);
  padding: 28px;
  overflow-wrap: anywhere;
}
.preview-body.table-preview {
  max-width: none;
  height: auto;
  min-height: 0;
  padding: 12px;
  overflow: hidden;
}
.preview-main.table-mode .preview-body.table-preview {
  flex: 1 1 auto;
  width: 80%;
}
.markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4,
.preview-body h1, .preview-body h2, .preview-body h3, .preview-body h4 {
  letter-spacing: 0;
  line-height: 1.25;
  margin: 1.35em 0 0.55em;
}
.markdown-body h1, .preview-body h1 { font-size: 28px; margin-top: 0; }
.markdown-body h2, .preview-body h2 {
  font-size: 22px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--line);
}
.markdown-body h3, .preview-body h3 { font-size: 18px; }
.markdown-body p, .preview-body p { margin: 0.75em 0; }
.markdown-body blockquote, .preview-body blockquote {
  margin: 1em 0;
  padding: 8px 12px;
  border-left: 4px solid var(--accent);
  background: var(--accent-soft);
  color: #33413d;
}
.markdown-body code, .preview-body code {
  background: var(--code);
  border-radius: 5px;
  padding: 1px 5px;
  font-family: Consolas, "SFMono-Regular", Menlo, monospace;
  font-size: 0.92em;
}
.markdown-body pre, .preview-body pre {
  overflow: auto;
  background: #17211f;
  color: #edf4f1;
  border-radius: 8px;
  padding: 14px;
}
.markdown-body pre code, .preview-body pre code {
  background: transparent;
  color: inherit;
  padding: 0;
}
.markdown-body ul, .markdown-body ol, .preview-body ul, .preview-body ol { padding-left: 1.45em; }
.table-wrap {
  width: 100%;
  max-width: 100%;
  overflow-x: scroll;
  overflow-y: auto;
  max-height: calc(100vh - 230px);
  border: 1px solid var(--line);
  border-radius: 8px;
  scrollbar-gutter: stable both-edges;
  scrollbar-color: #8fb1aa #edf2ef;
  scrollbar-width: auto;
}
.table-preview .table-wrap { height: 100%; max-height: none; }
.table-wrap::-webkit-scrollbar { width: 13px; height: 13px; }
.table-wrap::-webkit-scrollbar-track { background: #edf2ef; }
.table-wrap::-webkit-scrollbar-thumb { background: #8fb1aa; border: 3px solid #edf2ef; border-radius: 999px; }
table { width: max-content; min-width: 100%; border-collapse: collapse; font-size: 13px; table-layout: auto; }
.markdown-body table { width: 100%; font-size: 14px; }
th, td {
  border-bottom: 1px solid var(--line);
  border-right: 1px solid var(--line);
  padding: 8px 10px;
  vertical-align: top;
  min-width: 170px;
  max-width: 460px;
}
th { position: sticky; top: 0; z-index: 1; text-align: left; background: #f5f7f5; font-weight: 800; }
td { background: #fff; }
.data-table th:first-child, .data-table td:first-child {
  position: sticky;
  left: 0;
  min-width: 92px;
  max-width: 140px;
  z-index: 2;
}
.data-table th:first-child { z-index: 4; }
.data-table td:first-child { background: #fbfcfa; font-weight: 700; }
.data-table tbody tr:hover td { background: #f7fbf9; }
.data-table tbody tr:hover td:first-child { background: #eef7f3; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 14px; }
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  box-shadow: var(--shadow);
  padding: 16px;
  display: grid;
  gap: 9px;
}
.card h3 { margin: 0; font-size: 17px; line-height: 1.35; letter-spacing: 0; }
.card p { margin: 0; color: var(--muted); font-size: 14px; }
.tag { display: inline-flex; width: fit-content; padding: 2px 7px; border-radius: 8px; background: var(--accent-soft); color: var(--accent); font-size: 12px; font-weight: 800; }
tr[hidden], .hidden { display: none; }
@media (max-width: 920px) {
  .app { grid-template-columns: 1fr; }
  .app.table-mode { grid-template-columns: 300px minmax(0, 1fr); }
  aside { position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }
  .app.table-mode aside { position: sticky; top: 0; height: 100vh; border-right: 1px solid var(--line); border-bottom: 0; }
  main { padding: 18px; }
  .app.table-mode main { padding: 12px 18px; }
  .reader-head, .preview-head, .markdown-body, .preview-body { width: 100%; }
  .markdown-body, .preview-body { padding: 20px; }
  .preview-main.table-mode {
    height: 100vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .preview-body.table-preview { height: auto; min-height: 0; padding: 12px; }
}
"""


def html_page(title: str, body: str, data_id: str, data: object) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{COMMON_STYLE}</style>
</head>
<body>
{body}
<script id="{data_id}" type="application/json">{json_for_script(data)}</script>
</body>
</html>
"""


def build_index(project_title: str, papers: list[Paper], docs: list[dict[str, object]]) -> str:
    data = {
        "title": project_title,
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "direction": p.direction,
                "year": p.year,
                "venue": p.venue,
                "doi": p.doi,
                "preview": p.preview,
                "pdf": as_link(p.pdf_path),
            }
            for p in papers
        ],
        "docs": [{"id": d["id"], "title": d["title"], "kind": d["kind"]} for d in docs],
    }
    body = """
<div class="app">
  <aside>
    <div class="brand">
      <h1 id="projectTitle"></h1>
      <a href="preview.html">常用文件预览</a>
    </div>
    <input id="search" class="search" type="search" placeholder="搜索文献、方向、DOI">
    <div id="directionList" class="list"></div>
  </aside>
  <main>
    <section class="reader-head">
      <h2>文献索引</h2>
      <div class="meta-line" id="summary"></div>
    </section>
    <section id="cards" class="grid"></section>
  </main>
</div>
<script>
const data = JSON.parse(document.getElementById('indexData').textContent);
const search = document.getElementById('search');
const cards = document.getElementById('cards');
const directionList = document.getElementById('directionList');
let activeDirection = 'all';
document.getElementById('projectTitle').textContent = data.title;
function escapeText(value) {
  return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
}
function filtered() {
  const q = search.value.trim().toLowerCase();
  return data.papers.filter(p => {
    const inDirection = activeDirection === 'all' || p.direction === activeDirection;
    const haystack = [p.id,p.title,p.direction,p.year,p.venue,p.doi,p.preview].join(' ').toLowerCase();
    return inDirection && (!q || haystack.includes(q));
  });
}
function renderDirections() {
  const dirs = [...new Set(data.papers.map(p => p.direction || 'Unclassified'))].sort();
  const items = ['all', ...dirs];
  directionList.innerHTML = items.map(dir => `
    <button class="list-button ${dir === activeDirection ? 'active' : ''}" type="button" data-dir="${escapeText(dir)}">
      <span class="item-id">${dir === 'all' ? 'ALL' : escapeText(dir)}</span>
      <span class="item-title">${dir === 'all' ? '全部方向' : escapeText(dir)}</span>
    </button>`).join('');
  directionList.querySelectorAll('[data-dir]').forEach(btn => {
    btn.addEventListener('click', () => { activeDirection = btn.dataset.dir; render(); });
  });
}
function render() {
  const rows = filtered();
  document.getElementById('summary').textContent = `${rows.length} / ${data.papers.length} 篇文献`;
  cards.innerHTML = rows.map(p => `
    <article class="card">
      <span class="tag">${escapeText(p.id)}</span>
      <h3>${escapeText(p.title)}</h3>
      <p>${escapeText([p.year, p.venue].filter(Boolean).join(' · '))}</p>
      <p>${escapeText(p.direction)}</p>
      <p>${escapeText(p.preview)}</p>
      <div class="tool-row">
        <a class="button" href="reader.html?id=${encodeURIComponent(p.id)}">阅读翻译</a>
        ${p.pdf ? `<a class="button" href="${escapeText(p.pdf)}">PDF</a>` : ''}
      </div>
    </article>`).join('');
  renderDirections();
}
search.addEventListener('input', render);
render();
</script>
"""
    return html_page(project_title, body, "indexData", data)


def build_reader(project_title: str, papers: list[Paper]) -> str:
    data = {
        "title": project_title,
        "papers": [
            {
                "id": p.id,
                "title": p.title,
                "direction": p.direction,
                "year": p.year,
                "venue": p.venue,
                "doi": p.doi,
                "html": p.html,
                "pdf": as_link(p.pdf_path),
                "source": as_link(p.reader_path),
            }
            for p in papers
        ],
    }
    body = """
<div class="app">
  <aside>
    <div class="brand">
      <h1>Reader 文献阅读器</h1>
      <a href="index.html">返回索引</a>
    </div>
    <input id="readerSearch" class="search" type="search" placeholder="搜索文献编号、题名、方向">
    <div id="paperList" class="list"></div>
  </aside>
  <main>
    <header class="reader-head">
      <h2 id="paperTitle"></h2>
      <div class="meta-line" id="paperMeta"></div>
      <div class="reader-layout-tools">
        <div class="tool-row" id="toolRow"></div>
        <div class="nav-row">
          <button class="nav-button" id="prevPaper" type="button">上一篇</button>
          <button class="nav-button" id="nextPaper" type="button">下一篇</button>
        </div>
      </div>
    </header>
    <article id="markdownBody" class="markdown-body"></article>
  </main>
</div>
<script>
const data = JSON.parse(document.getElementById('readerData').textContent);
const state = { activeId: '', query: '' };
const paperList = document.getElementById('paperList');
const search = document.getElementById('readerSearch');
const title = document.getElementById('paperTitle');
const meta = document.getElementById('paperMeta');
const tools = document.getElementById('toolRow');
const body = document.getElementById('markdownBody');
function escapeText(value) {
  return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
}
function activeIndex() { return data.papers.findIndex(p => p.id === state.activeId); }
function filteredPapers() {
  const q = state.query.trim().toLowerCase();
  if (!q) return data.papers;
  return data.papers.filter(p => [p.id,p.title,p.direction,p.year,p.venue,p.doi].join(' ').toLowerCase().includes(q));
}
function renderList() {
  paperList.innerHTML = filteredPapers().map(p => `
    <button class="list-button ${p.id === state.activeId ? 'active' : ''}" type="button" data-id="${escapeText(p.id)}">
      <span class="item-id">${escapeText(p.id)}</span>
      <span class="item-title">${escapeText(p.title)}</span>
      <span class="item-meta">${escapeText(p.direction || '')}</span>
    </button>`).join('');
  paperList.querySelectorAll('[data-id]').forEach(btn => btn.addEventListener('click', () => selectPaper(btn.dataset.id)));
}
function selectPaper(id, push = true) {
  const paper = data.papers.find(p => p.id === id) || data.papers[0];
  if (!paper) return;
  state.activeId = paper.id;
  title.textContent = `${paper.id} ${paper.title}`;
  document.title = `${paper.id} · ${paper.title}`;
  meta.textContent = [paper.direction, paper.year, paper.venue, paper.doi].filter(Boolean).join(' · ');
  tools.innerHTML = [
    paper.pdf ? `<a class="tool-link" href="${escapeText(paper.pdf)}">PDF</a>` : '',
    paper.source ? `<a class="tool-link" href="${escapeText(paper.source)}">reader.md</a>` : ''
  ].filter(Boolean).join('');
  body.innerHTML = paper.html || '<p>暂无内容。</p>';
  renderList();
  if (push) {
    const url = new URL(window.location.href);
    url.searchParams.set('id', paper.id);
    history.replaceState(null, '', url);
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
function move(delta) {
  const items = data.papers;
  const index = activeIndex();
  const next = items[(index + delta + items.length) % items.length];
  if (next) selectPaper(next.id);
}
search.addEventListener('input', e => { state.query = e.target.value; renderList(); });
document.getElementById('prevPaper').addEventListener('click', () => move(-1));
document.getElementById('nextPaper').addEventListener('click', () => move(1));
const params = new URLSearchParams(window.location.search);
selectPaper(params.get('id') || (data.papers[0] && data.papers[0].id) || '', false);
</script>
"""
    return html_page(f"{project_title} · Reader", body, "readerData", data)


def build_preview(project_title: str, docs: list[dict[str, object]]) -> str:
    data = {"title": project_title, "docs": docs}
    body = """
<div id="previewApp" class="app preview markdown-mode">
  <aside>
    <div class="brand">
      <h1>常用文件预览</h1>
      <a href="index.html">返回索引</a>
    </div>
    <input id="previewSearch" class="search" type="search" placeholder="搜索当前预览内容">
    <div id="docList" class="list"></div>
  </aside>
  <main id="previewMain" class="preview-main markdown-mode">
    <header class="preview-head">
      <h2 id="docTitle"></h2>
      <div class="meta-line" id="docMeta"></div>
      <div class="meta-line" id="docDescription"></div>
      <div class="tool-row" id="toolRow"></div>
    </header>
    <article id="previewBody" class="preview-body"></article>
  </main>
</div>
<script>
const data = JSON.parse(document.getElementById('previewData').textContent);
const state = { activeId: '', query: '' };
const app = document.getElementById('previewApp');
const main = document.getElementById('previewMain');
const docList = document.getElementById('docList');
const search = document.getElementById('previewSearch');
const title = document.getElementById('docTitle');
const meta = document.getElementById('docMeta');
const description = document.getElementById('docDescription');
const tools = document.getElementById('toolRow');
const body = document.getElementById('previewBody');
function escapeText(value) {
  return String(value || '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[ch]));
}
function renderList() {
  docList.innerHTML = data.docs.map(doc => `
    <button class="list-button ${doc.id === state.activeId ? 'active' : ''}" type="button" data-id="${escapeText(doc.id)}">
      <span class="item-title">${escapeText(doc.title)}</span>
      <span class="item-meta">${escapeText(doc.description)}</span>
    </button>`).join('');
  docList.querySelectorAll('[data-id]').forEach(btn => btn.addEventListener('click', () => selectDoc(btn.dataset.id)));
}
function applySearch() {
  const doc = data.docs.find(item => item.id === state.activeId);
  const q = state.query.trim().toLowerCase();
  if (!doc) return;
  if (doc.kind === 'csv') {
    const rows = [...body.querySelectorAll('tbody tr')];
    let visible = 0;
    rows.forEach(row => {
      const show = !q || row.textContent.toLowerCase().includes(q);
      row.hidden = !show;
      if (show) visible += 1;
    });
    meta.textContent = `${doc.rowCount} 行 / ${doc.colCount} 列${q ? `，当前匹配 ${visible} 行` : ''}`;
  } else {
    meta.textContent = `${doc.rowCount} 行 Markdown`;
  }
}
function selectDoc(id, push = true) {
  const doc = data.docs.find(item => item.id === id) || data.docs[0];
  if (!doc) return;
  state.activeId = doc.id;
  state.query = '';
  search.value = '';
  const mode = doc.kind === 'csv' ? 'table-mode' : 'markdown-mode';
  app.className = `app preview ${mode}`;
  main.className = `preview-main ${mode}`;
  title.textContent = doc.title;
  document.title = `${doc.title} · 预览`;
  description.textContent = doc.description || '';
  tools.innerHTML = doc.source ? `<a class="tool-link" href="${escapeText(doc.source)}">打开原始文件</a>` : '';
  body.className = `preview-body ${doc.kind === 'csv' ? 'table-preview' : 'markdown-preview'}`;
  body.innerHTML = doc.html || '<p>暂无内容。</p>';
  renderList();
  applySearch();
  if (push) {
    const url = new URL(window.location.href);
    url.searchParams.set('doc', doc.id);
    history.replaceState(null, '', url);
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
search.addEventListener('input', e => { state.query = e.target.value; applySearch(); });
const params = new URLSearchParams(window.location.search);
selectDoc(params.get('doc') || (data.docs[0] && data.docs[0].id) || '', false);
</script>
"""
    return html_page(f"{project_title} · Preview", body, "previewData", data)


def project_title_from_path(project: Path, explicit: str | None) -> str:
    return explicit.strip() if explicit else project.name


def build_site(project: Path, out_dir: Path, title: str, dry_run: bool = False) -> dict[str, object]:
    papers = collect_papers(project)
    docs = collect_preview_docs(project)
    result = {
        "project": str(project),
        "out": str(out_dir),
        "papers": len(papers),
        "preview_docs": len(docs),
        "directions": sorted({p.direction for p in papers}),
    }
    if dry_run:
        return result
    out_dir.mkdir(parents=True, exist_ok=True)
    write_text(out_dir / "index.html", build_index(title, papers, docs))
    write_text(out_dir / "reader.html", build_reader(title, papers))
    write_text(out_dir / "preview.html", build_preview(title, docs))
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build nature-summary static reader pages.")
    parser.add_argument("--project", required=True, help="Project folder containing readers/, metadata/, draft/.")
    parser.add_argument("--out", help="Output folder. Defaults to the project folder.")
    parser.add_argument("--title", help="Display title. Defaults to the project folder name.")
    parser.add_argument("--dry-run", action="store_true", help="Scan and report without writing HTML files.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    project = Path(args.project).expanduser().resolve()
    if not project.exists():
        print(f"Project folder does not exist: {project}", file=sys.stderr)
        return 2
    out_dir = Path(args.out).expanduser().resolve() if args.out else project
    title = project_title_from_path(project, args.title)
    result = build_site(project, out_dir, title, dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not args.dry_run:
        print(f"wrote={out_dir / 'index.html'}")
        print(f"wrote={out_dir / 'reader.html'}")
        print(f"wrote={out_dir / 'preview.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
