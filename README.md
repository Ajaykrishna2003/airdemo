# airdemo — Blindfastener

A frontend and Python backend using the supplied Excel workbook.

## Run

First, place your Excel workbook at `data/blindfastener.xlsx`. The workbook is kept local and is not included in this repository.

With Python 3.10 or newer, open a terminal in this folder:

```powershell
python -m pip install -r requirements.txt
python backend/server.py
```

Open http://127.0.0.1:8000 in your browser. Keep the terminal running; press Ctrl+C to stop.
On this computer, `start.ps1` also supports the bundled Codex Python runtime.
Do not open `frontend/index.html` directly: the frontend needs the API server.
This folder contains the frontend and backend application.

## Files

- `frontend/index.html`: search and results UI.
- `frontend/styles.css`: responsive styling; J–AA blue, AE–BN green, BO marking, BP technical specification, and BQ–CB strength fields in key–value rows.
- `frontend/app.js`: API calls, record selection, result display and error states.
- `backend/server.py`: read-only API, Excel loading, lookup rules and static frontend serving.
- `data/blindfastener.xlsx`: copy of the supplied workbook. The original remains unchanged.

## Behavior

Select a part number from the database dropdown, then click Find fastener. The finish / diameter / grip search has been removed.
Part number matching ignores case and surrounding whitespace.
Multiple matches require record selection. Fields without values are hidden in all five sets. Set 1 keeps material, finish and lubricant together by component; entirely empty component rows and groups are hidden. Numeric zero remains visible.
Changing inputs clears stale results.

The selected part shows column B and Revision: column C beneath its part number.

For electrical bonding = No, CC/CD + substrate material and CG/CH + substrate material match galvanic A/B/C and return D/E. With Nut or washer side selected for a substrate, CE/CF + substrate material + substrate finish match G/H/I/J and return K/L. Substrate finish is ignored for the two A/B/C lookups. Results for all rows appear in one table. Add up to five substrate rows; each has its own nut-side checkbox. For electrical bonding = Yes, CC/CD and CG/CH plus substrate material match U/V/W and return X/Y; checked nut-side rows use CE/CF plus substrate material/finish to match AA/AB/AC/AD and return AE only. AF is not used. Both modes share the same five-row limit and conditional nut-side checks. Matching ignores case and surrounding spaces but does not infer material aliases. Missing source values and unmatched or conflicting rows have explicit statuses.

## Replace the workbook

Stop the server, replace `data/blindfastener.xlsx`, then restart it. Alternatively:

```powershell
python backend/server.py --workbook "C:\path\updated.xlsx" --port 8000
```

Workbook contents are loaded at server startup. Required sheet names are
`Database` and `Galvanic compatability`. This version expects the database
header on row 2 and records beginning on row 3, with at least columns A–CB. All supplied columns are retained in API records.
Formula cells use values cached by Excel; save/recalculate in Excel before loading
if formulas were changed.

## API

- `GET /api/metadata`: headers, record count and dropdown options.
- `GET /api/fasteners?mode=part&part=ABS0546D402`: matching records.
- Combination searches are rejected with HTTP 400.
- `POST /api/compatibility`: JSON with part, mode (yes/no), and substrates (1–5 objects with material, finish, and boolean nutSide).

Missing or invalid inputs return HTTP 400. Unknown routes and missing parts in
compatibility requests return HTTP 404.

## Tests

The integration tests require the local workbook. Synthetic lookup tests use generated data. Run the display checks with `node tests/test_display.cjs`.

```powershell
python -m unittest discover -s tests -v
```

This is a local development application bound to 127.0.0.1. It has no accounts,
write endpoints, or public deployment configuration.



For electrical bonding = No, a separate bolt-nut check matches CC/CD/CE/CF against galvanic N/O/P/Q and returns R (compatibility) and S (comments). This runs once per selected fastener regardless of substrate count or nut-side checkbox, and appears below the substrate results. For Yes, the same CC/CD/CE/CF keys match AH/AI/AJ/AK and return AL (compatibility) and AM (comments), in the same separate container below substrate results.
