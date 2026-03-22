# Salesforce PDF Filler — Rules for Claude Code

## Architecture
- 3-layer: Python Core (engine) → FastAPI (API) → n8n (trigger layer)
- Config-driven: field_map.json controls ALL field mapping — code never changes for new PDFs
- PDF template agnostic: works with any AcroForm PDF

## Rules
1. **Never hardcode field mappings** — ALL mappings live in `data/field_map.json`
2. **Never expose credentials** — SF creds live only in `.env`, never committed
3. **Always discover before mapping** — Run `discover` on any new PDF template first
4. **Always flatten PDFs** — Unless explicitly asked not to (prevents blank-field rendering bugs)
5. **Logs to data/ folder** — Never project root
6. **API returns base64 by default** — n8n expects base64 binary data for file handling
7. **ContentVersion for uploads** — Use modern Salesforce Files API, not legacy Attachment
8. **Error gracefully** — Never crash on missing fields, use empty string defaults

## File Responsibilities
| File | Does | Does NOT |
|------|------|----------|
| `salesforce_client.py` | Connect, query, discover SF objects | Fill PDFs, map fields |
| `pdf_filler.py` | Fill forms, flatten, validate | Query Salesforce |
| `field_mapper.py` | Map SF fields to PDF fields | Query SF or fill PDFs |
| `uploader.py` | Upload to SF, send email | Anything else |
| `api.py` | HTTP endpoints for n8n | Business logic (delegates to core) |
| `run.py` | CLI commands | Business logic (delegates to core) |

## Adding a New PDF Template
1. Place template in `templates/`
2. Run `python run.py discover templates/new_template.pdf --save`
3. Edit `data/field_map.json` to map SF fields to discovered PDF fields
4. Test: `python run.py fill --lead-id XYZ --template templates/new_template.pdf --dry-run`
5. Done. No code changes needed.

## Stack
- Python 3.11+, simple-salesforce, fillpdf, FastAPI, Click
