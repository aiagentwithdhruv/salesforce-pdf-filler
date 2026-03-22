# Salesforce Multi-Form to Fillable PDF — Automation Workflow

> **Requestor:** Gopikrishna Pujari (+91 88015 72348)
> **Context:** Euron Future Proof AI Automation Bootcamp student
> **Ask:** Read data from multiple Salesforce forms → populate a single fillable PDF
> **Status:** BUILT (Python + FastAPI + n8n workflow)
> **n8n Workflow ID:** `JRgbD1qPFmTjb9tJ` (11 nodes, inactive — activate after SF credentials configured)
> **n8n Link:** https://n8n.aiwithdhruv.cloud/workflow/JRgbD1qPFmTjb9tJ

---

## Problem Statement

Read data from **multiple Salesforce objects/forms** (Leads, Contacts, Opportunities, Custom Objects, etc.) and populate a **single fillable PDF template** with that merged data. The filled PDF should be:
- Flattened (non-editable) for archival/sending
- Optionally uploaded back to Salesforce as an attachment
- Optionally emailed to the relevant contact

---

## Two Architecture Options

### Option 1: n8n Workflow (No-Code, Visual)

**Best for:** Event-driven triggers, non-technical team adjustments, connecting to existing n8n automations.

```
┌─────────────────────────────────────────────────────────────────┐
│                     n8n WORKFLOW FLOW                            │
│                                                                 │
│  [Salesforce Trigger]  ──or──  [Schedule / Manual Trigger]      │
│         │                              │                        │
│         ▼                              ▼                        │
│  [Salesforce Node — Get Lead (all fields)]                      │
│         │                                                       │
│         ▼                                                       │
│  [Salesforce Node — Get related Contact/Account/Opportunity]    │
│         │                                                       │
│         ▼                                                       │
│  [Code Node — Merge all objects into flat JSON]                 │
│  {                                                              │
│    "firstName": "John",                                         │
│    "lastName": "Doe",                                           │
│    "company": "Acme Corp",                                      │
│    "dealAmount": "50000",                                       │
│    ...matches PDF field names exactly                           │
│  }                                                              │
│         │                                                       │
│         ▼                                                       │
│  [HTTP Request — Fetch blank PDF template from S3/GDrive]       │
│         │                                                       │
│         ▼                                                       │
│  [Doc Fill Node (n8n-nodes-doc-filler) — Fill PDF fields]       │
│         │                                                       │
│         ├──▶ [Salesforce Node — Upload as ContentVersion]       │
│         │                                                       │
│         └──▶ [Email Node — Send filled PDF to contact]          │
└─────────────────────────────────────────────────────────────────┘
```

**Required n8n Nodes:**
| Node | Type | Purpose |
|------|------|---------|
| Salesforce Trigger | Built-in | Fires on Lead/Contact create/update |
| Salesforce | Built-in | CRUD on Account, Contact, Lead, Opportunity, Custom Objects |
| Code | Built-in | Merge multi-object data into flat JSON matching PDF fields |
| HTTP Request | Built-in | Fetch PDF template from cloud storage |
| Doc Fill | Community (`n8n-nodes-doc-filler`) | Fill AcroForm fields in PDF |
| Email / Gmail | Built-in | Send filled PDF |

**n8n Community Node Install:**
```
Settings → Community Nodes → Install → n8n-nodes-doc-filler
```
Provides 3 nodes:
- `Doc Get Form Fields` — extract all field names from PDF template (run once to discover mapping)
- `Doc Fill` — fill fields via JSON config
- `Doc Create Field` — add text at exact XY coordinates (for non-form PDFs)

**Salesforce Auth in n8n:**
1. Create a Connected App in Salesforce Setup
2. In n8n: Credentials → Salesforce → OAuth2
3. Paste Consumer Key + Consumer Secret + Callback URL
4. Authorize → Done

**Pros:** Visual, easy to modify, native Salesforce trigger, zero Python needed
**Cons:** Community node required for PDF filling (self-hosted only), less flexible for complex logic

---

### Option 2: Agentic Python Script (Code-First, Extensible)

**Best for:** Batch processing, complex multi-object joins, conditional field mapping, scheduled runs, engineering-owned pipelines.

#### Project Structure
```
Salesforce_PDF_Filler/
├── WORKFLOW.md              # This file
├── CLAUDE.md                # Rules for Claude Code
├── run.py                   # CLI entry point
├── requirements.txt         # Dependencies
├── .env.example             # Environment template
├── src/
│   ├── __init__.py
│   ├── config.py            # Env vars, paths, constants
│   ├── salesforce_client.py # Salesforce connection + queries
│   ├── pdf_filler.py        # PDF field discovery + filling + flattening
│   ├── field_mapper.py      # Salesforce fields → PDF field name mapping
│   ├── uploader.py          # Upload filled PDF back to Salesforce
│   └── logger.py            # Run logs (JSON + markdown)
├── templates/
│   └── .gitkeep             # PDF templates go here (or fetched from S3)
├── output/
│   └── .gitkeep             # Filled PDFs saved here
└── data/
    ├── field_map.json       # Salesforce field → PDF field mapping config
    └── run_log.json         # Processing history
```

#### Core Flow (Python)
```python
# run.py — simplified flow

from src.config import settings
from src.salesforce_client import SalesforceClient
from src.pdf_filler import PDFFiller
from src.field_mapper import FieldMapper
from src.uploader import Uploader

# 1. Connect to Salesforce
sf = SalesforceClient()

# 2. Query multiple objects
lead = sf.get_lead(lead_id)
contact = sf.get_contact(contact_id)
opportunity = sf.get_opportunity(opp_id)
custom_data = sf.query_custom("SELECT ... FROM Custom_Form__c WHERE ...")

# 3. Merge all data into flat dict
mapper = FieldMapper("data/field_map.json")
pdf_data = mapper.merge_and_map(lead, contact, opportunity, custom_data)

# 4. Fill PDF template
filler = PDFFiller("templates/intake_form.pdf")
filler.discover_fields()          # Run once to see all field names
filler.fill(pdf_data)             # Fill with mapped data
filler.flatten("output/filled.pdf")  # Make non-editable

# 5. Upload back to Salesforce (optional)
uploader = Uploader(sf)
uploader.attach_to_record(lead_id, "output/filled.pdf")

# 6. Email (optional)
# uploader.email_pdf(lead["Email"], "output/filled.pdf")
```

#### Key Libraries
```
# requirements.txt
simple-salesforce==1.12.6    # Salesforce API client
fillpdf==0.7.3               # PDF form filling (wraps pdfrw2)
python-dotenv==1.0.1         # Environment management
click==8.1.7                 # CLI interface
```

#### CLI Commands
```bash
# Discover PDF field names (run first with any new template)
python run.py discover templates/intake_form.pdf

# Fill single record
python run.py fill --lead-id 00Q1234567890AB

# Batch fill (all leads from today)
python run.py batch --since today

# Dry run (show what would be filled, don't write PDF)
python run.py fill --lead-id 00Q1234567890AB --dry-run
```

#### Field Mapping Config (data/field_map.json)
```json
{
  "_description": "Maps Salesforce field paths to PDF form field names",
  "_instructions": "Run 'python run.py discover template.pdf' to see all PDF field names",
  "mappings": [
    {"sf_object": "Lead", "sf_field": "FirstName", "pdf_field": "firstName"},
    {"sf_object": "Lead", "sf_field": "LastName", "pdf_field": "lastName"},
    {"sf_object": "Lead", "sf_field": "Email", "pdf_field": "email"},
    {"sf_object": "Lead", "sf_field": "Phone", "pdf_field": "phone"},
    {"sf_object": "Lead", "sf_field": "Company", "pdf_field": "company"},
    {"sf_object": "Opportunity", "sf_field": "Amount", "pdf_field": "dealAmount"},
    {"sf_object": "Opportunity", "sf_field": "CloseDate", "pdf_field": "closeDate"},
    {"sf_object": "Contact", "sf_field": "MailingStreet", "pdf_field": "address"},
    {"sf_object": "Custom_Form__c", "sf_field": "Notes__c", "pdf_field": "additionalNotes"}
  ],
  "defaults": {
    "dateFormat": "YYYY-MM-DD",
    "emptyValue": "",
    "checkboxTrue": "Yes",
    "checkboxFalse": "Off"
  }
}
```

**Pros:** Full control, batch mode, complex joins, testable, deployable anywhere
**Cons:** Requires Python knowledge, no visual editor

---

## Decision Matrix

| Factor | n8n (Option 1) | Python (Option 2) |
|--------|----------------|-------------------|
| Triggered by SF record change | Native trigger node | Needs polling/webhook/cron |
| Multiple objects, complex joins | Multiple nodes + Code node | Native Python — easier |
| Non-technical team adjusts it | Yes (visual) | No |
| Batch mode (100+ records/run) | Loop node (slower) | Python for-loop (fast) |
| Conditional field mapping | Code node required | Native Python |
| PDF filling cost | Free (community node) | Free (fillpdf lib) |
| Schedule-based runs | Built-in cron trigger | Cron / Modal / Lambda |
| Upload PDF back to Salesforce | Native Salesforce node | simple-salesforce API |
| Deployment | Self-hosted n8n or n8n Cloud | VPS / Docker / Modal |
| Best for POC/demo | Faster to show | More robust |

---

## Critical Technical Notes

### Salesforce Side
1. **Auth for production:** Use OAuth2 Connected App + JWT Bearer flow (not username+password)
2. **API limits:** Developer/free orgs = 15K calls/day. Enterprise = 100K+
3. **Object discovery:** Run `sf.describe()["sobjects"]` to list all objects. Run `sf.Lead.describe()["fields"]` for field names
4. **Custom objects:** End with `__c` (e.g., `Intake_Form__c`). Custom fields also end with `__c`
5. **File upload:** Modern orgs use `ContentVersion` (Salesforce Files). Older use `Attachment`. Check which the client's org uses
6. **Survey data:** If using Salesforce Surveys, objects are `Survey` → `SurveyQuestion` → `SurveyQuestionResponse`. Requires Feedback Management license

### PDF Side
1. **ALWAYS discover fields first:** `fillpdfs.get_form_fields("template.pdf")` — field names are often not what you'd expect (e.g., "First Name" label might be stored as `Text_1`)
2. **Flatten after filling:** Without `flatten_pdf()`, some viewers show blank fields
3. **Checkboxes:** Use `"Yes"` for checked, `"Off"` for unchecked
4. **Dropdowns:** Value must exactly match one of the dropdown options in the PDF
5. **Template storage:** Keep blank template in S3/Google Drive, fetch at runtime. Never hardcode local paths
6. **Non-AcroForm PDFs:** If the PDF has no form fields (just visual boxes), you'll need to use coordinate-based text placement (`Doc Create Field` in n8n or `reportlab` overlay in Python)

### n8n-Specific
1. **Community node (`n8n-nodes-doc-filler`):** Only works on self-hosted n8n or cloud plans allowing community nodes
2. **Alternative:** If community nodes aren't available, use HTTP Request to call a Python microservice (FastAPI endpoint that accepts JSON + returns filled PDF)
3. **Salesforce Trigger:** Fires on Create or Update for any standard/custom object

---

## What We Need From Gopikrishna Before Building

1. **Which Salesforce objects?** — Lead, Contact, Opportunity, Custom Objects? Names of custom objects?
2. **PDF template** — Does he already have a fillable PDF? Or does he need us to create one?
3. **Field mapping** — Which Salesforce fields go into which PDF fields?
4. **Trigger type** — On-demand? On record create/update? Scheduled batch?
5. **Output** — Just save PDF? Upload back to Salesforce? Email to someone?
6. **Salesforce edition** — Developer? Enterprise? (affects API limits)
7. **n8n setup** — Self-hosted or n8n Cloud? (affects community node availability)
8. **Preference** — Option 1 (n8n) or Option 2 (Python)?

---

## Recommended Approach

**For a POC (what Gopikrishna asked for):** Start with **Option 2 (Python)** because:
- Faster to demonstrate end-to-end without n8n setup
- Can run locally with his Salesforce credentials
- `fillpdf` is dead simple — 3 lines to fill a PDF
- Easy to convert to n8n later (wrap in FastAPI endpoint)

**For production:** Either works. If his team uses n8n → Option 1. If engineering-owned → Option 2.

**Hybrid approach (best of both):**
- Build the Python core (Option 2) as a FastAPI microservice
- Call it from n8n via HTTP Request node
- Gets visual workflow + full Python power
- Can also run standalone via CLI

---

## References

- [simple-salesforce (Python)](https://github.com/simple-salesforce/simple-salesforce)
- [fillpdf (Python)](https://github.com/t-houssian/fillpdf)
- [n8n Salesforce Node](https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.salesforce/)
- [n8n-nodes-doc-filler](https://github.com/davidruzicka/n8n-nodes-doc-filler)
- [Salesforce REST API](https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/)
- [Salesforce Survey Object Model](https://developer.salesforce.com/docs/atlas.en-us.object_reference.meta/object_reference/sforce_api_objects_salesforce_surveys_object_model.htm)
