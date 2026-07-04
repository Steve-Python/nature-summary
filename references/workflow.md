# Nature Summary Workflow Details

## 0. Intake

Capture the user's topic, scope, preferred language, target field, time window, and whether institutional browser access is available. If the user already has PDFs, skip directly to inventory and classification.

Recommended project folders:

```text
metadata/
PDFs/
readers/
draft/
archive/
logs/
```

Required metadata files:

```text
metadata/seed_reviews.csv
metadata/direction_map.md
metadata/literature_manifest.csv
metadata/download_manifest.csv
metadata/manual_download_queue.csv
```

## 1. Open-Access Review Seed Search

Use `nature-academic-search` with review-oriented queries:

```text
"<topic>" review open access
"<topic>" recent advances review
"<topic>" applications review
"<topic>" challenges opportunities review
```

Prefer 5-10 review articles that are:

- open access or institution-authorized.
- recent enough for the topic.
- broad enough to reveal the field structure.
- explicit about mechanisms, applications, methods, gaps, or future directions.

Download with `nature-downloader`, then read abstracts, figures, conclusions, and section headings. Produce `metadata/direction_map.md` with 3-8 directions.

## 2. Direction-Specific Search

For each direction, search 5-10 focused papers. Keep search terms, inclusion logic, and exclusions in `metadata/search_log.md`.

Manifest columns:

```text
id,direction_id,direction,title,year,venue,doi,url,source_type,priority,download_status,pdf_path,reader_path,notes
```

Use stable IDs:

```text
R01-R10  seed reviews
D1-01    direction 1 paper 1
D2-01    direction 2 paper 1
```

Download status values:

```text
downloaded
open_access_downloaded
available_not_downloaded
manual_download_waiting_user
publisher_verification_waiting_user
carsi_waiting_user
library_no_permission
no_authorized_pdf_found
failed_after_retry
```

When automatic download is blocked, open the paper page in the user's browser, add it to `manual_download_queue.csv`, and wait for the user to finish downloading.

## 3. Inventory And Archive

After the user reports that downloads are complete:

1. Inventory the download folder and project `PDFs/`.
2. Match PDFs by DOI, title words, and user-provided filenames.
3. Place files under `PDFs/<direction-id>/`.
4. Move duplicate or superseded files into `archive/duplicates/`.
5. Update `metadata/download_manifest.csv`.

Never delete user-downloaded PDFs during cleanup. Archive instead.

## 4. Coarse Reader Pass

Use `nature-reader` to produce `readers/<id>/paper.md` for every paper. Default scope:

- citation metadata.
- abstract original and Chinese translation.
- conclusion/discussion original and Chinese translation.
- key evidence for the review.
- limitations for this paper.
- one-paragraph relevance note.

Also save source-grounding notes when available:

```text
readers/<id>/source_map.json
readers/<id>/translation_notes.md
```

## 5. Review Draft

Before drafting, build:

```text
draft/review_outline.md
draft/evidence_gap_table.md
```

Then use `nature-writing` in review-paper mode. The review should:

- introduce the user's topic and why it matters.
- organize sections by the direction map, not by download order.
- cite evidence from generated readers.
- separate established findings from emerging hypotheses.
- include a section on limitations, gaps, and future work.

Save the main manuscript as:

```text
draft/review.md
```

## 6. Web Preview

Run:

```powershell
python <skill-dir>\scripts\build_reader.py --project "<project-folder>"
```

Expected outputs:

```text
index.html
reader.html
preview.html
```

Open `index.html` directly or serve the project folder locally. The pages embed Markdown/CSV content as JSON and do not require a backend.

## Final Deep-Reading Checkpoint

Ask the user which directions deserve full-paper translation. For selected directions:

1. Archive existing coarse readers under `archive/coarse_readers/<timestamp>/`.
2. Use `nature-reader` to build full translated readers.
3. Replace `readers/<id>/paper.md`.
4. Rebuild the preview pages.
5. Update `draft/review.md` only where new evidence changes claims.

