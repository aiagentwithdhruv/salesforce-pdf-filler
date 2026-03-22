# Salesforce Multi-Form to PDF Filler

Read data from multiple Salesforce objects (Leads, Contacts, Opportunities, Custom Objects) and auto-fill a single PDF form. Two methods included — pick what works for you.

```
Salesforce (any object) → field_map.json → Filled PDF → Email / Upload / Save
```

## Two Methods

| Method | Best For | Setup Time |
|--------|----------|------------|
| **Python CLI + API** | Full control, batch processing, complex logic | 10 min |
| **n8n Workflow** | Visual automation, event-driven triggers, no code | 5 min |

Both methods use the same core: a config-driven field mapping (`field_map.json`) that maps Salesforce fields to PDF form fields. Change the config — not the code.

---

## Method 1: Python (CLI + FastAPI)

### Quick Start

```bash
# 1. Clone and install
git clone https://github.com/aiagentwithdhruv/salesforce-pdf-filler.git
cd salesforce-pdf-filler
pip install -r requirements.txt

# 2. Configure credentials
cp .env.example .env
# Edit .env with your Salesforce credentials

# 3. Drop your PDF template
cp /path/to/your/form.pdf templates/

# 4. Discover PDF field names (IMPORTANT — do this first!)
python run.py discover templates/form.pdf --save

# 5. Edit field mapping
# Open data/field_map.json and map Salesforce fields to the PDF field names you just discovered

# 6. Fill a PDF
python run.py fill --lead-id 00Q1234567890AB

# 7. Or batch fill all leads from today
python run.py batch --since today
```

### All CLI Commands

```bash
python run.py discover <template.pdf>           # See all PDF field names
python run.py discover <template.pdf> --save     # Save field report to JSON

python run.py fill --lead-id <ID>                # Fill from a Lead
python run.py fill --lead-id <ID> --contact-id <ID>  # Fill from Lead + Contact
python run.py fill --lead-id <ID> --dry-run      # Preview without writing PDF
python run.py fill --lead-id <ID> --upload       # Fill + upload back to Salesforce
python run.py fill --lead-id <ID> --no-flatten   # Keep PDF editable

python run.py batch --since 2026-03-01           # Batch fill since date
python run.py batch --since today --upload       # Batch fill + upload

python run.py suggest <template.pdf>             # Auto-suggest field mapping
python run.py suggest <template.pdf> --objects Lead,Contact --save

python run.py stats                              # View run history
python run.py serve                              # Start API server (port 8100)
```

### API Endpoints (FastAPI)

Start with `python run.py serve` — runs on `http://localhost:8100`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/fill` | POST | Fill PDF from Salesforce record IDs |
| `/fill/raw` | POST | Fill PDF from raw JSON (no Salesforce needed) |
| `/discover` | GET | List all form fields in a PDF template |
| `/suggest` | POST | Auto-suggest field mapping |
| `/health` | GET | Health check |
| `/stats` | GET | Run statistics |

**Example — Fill from raw JSON:**
```bash
curl -X POST http://localhost:8100/fill/raw \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "firstName": "John",
      "lastName": "Doe",
      "email": "john@example.com",
      "company": "Acme Corp"
    },
    "return_base64": true
  }'
```

---

## Method 2: n8n Workflow

### Quick Start

1. Open your n8n instance
2. Go to **Workflows → Import from File**
3. Select `n8n/salesforce-pdf-filler-workflow.json`
4. Add your **Salesforce credentials** (Settings → Credentials → Salesforce OAuth2)
5. Edit the **"Merge SF Data to PDF Fields"** Code node to match your PDF field names
6. Start the Python API: `python run.py serve`
7. Activate the workflow

### Workflow Flow

```
[Salesforce Trigger / Manual]
        ↓
[Get Lead Details]
        ↓
[Code Node — Map SF fields to PDF fields]
        ↓
[HTTP Request → Python API (localhost:8100)]
        ↓
[Check Success]
   ├── ✅ → [Convert to File] → [Email PDF]
   └── ❌ → [Log Error]
```

### Nodes (11 total)

| Node | Purpose |
|------|---------|
| Salesforce Trigger | Auto-fires on Lead create/update |
| Manual Trigger | For testing — click to run |
| Set Lead ID | Set test Lead ID for manual runs |
| Get Lead Details | Fetch Lead data from Salesforce |
| Merge SF Data to PDF Fields | **Edit this** — map your SF fields to PDF fields |
| Fill PDF via API | Calls Python FastAPI server |
| Check Fill Success | Routes success/failure |
| Convert Base64 to File | Converts API response to PDF file |
| Email Filled PDF | Sends PDF as email attachment |
| Log Error | Logs failures for debugging |

---

## Field Mapping (The Key File)

`data/field_map.json` controls everything. Edit this file to match your PDF template — no code changes needed.

### How to set it up:

**Step 1:** Discover your PDF field names
```bash
python run.py discover templates/your_form.pdf
```
Output:
```
  [T]  Text1
  [T]  Text2
  [x]  CheckBox1
  [T]  email_field
  ...
```

**Step 2:** Edit `data/field_map.json` to map Salesforce fields to those PDF field names:
```json
{
  "mappings": [
    {"sf_object": "Lead", "sf_field": "FirstName", "pdf_field": "Text1", "type": "text"},
    {"sf_object": "Lead", "sf_field": "LastName", "pdf_field": "Text2", "type": "text"},
    {"sf_object": "Lead", "sf_field": "Email", "pdf_field": "email_field", "type": "text"},
    {"sf_object": "Opportunity", "sf_field": "Amount", "pdf_field": "deal_amount", "type": "currency"},
    {"sf_object": "Opportunity", "sf_field": "CloseDate", "pdf_field": "close_date", "type": "date"}
  ],
  "defaults": {
    "dateFormat": "YYYY-MM-DD",
    "emptyValue": "",
    "checkboxTrue": "Yes",
    "checkboxFalse": "Off"
  }
}
```

### Supported field types:
- `text` — plain string
- `date` — formatted date (configurable via `dateFormat`)
- `currency` — formatted as `$1,234.56`
- `checkbox` — `Yes` / `Off`

### Auto-suggest mapping:
```bash
python run.py suggest templates/your_form.pdf --objects Lead,Contact,Opportunity --save
```
This fuzzy-matches PDF field names to Salesforce field labels and generates a starting `field_map.json`.

---

## Configuration

### `.env` file

```bash
# Salesforce credentials
SF_USERNAME=your_username@example.com
SF_PASSWORD=your_password
SF_SECURITY_TOKEN=your_token          # Settings → My Personal Information → Reset Security Token
SF_DOMAIN=login                        # "login" for production, "test" for sandbox

# App settings
FLATTEN_PDF=true                       # Make filled PDF non-editable
UPLOAD_TO_SF=false                     # Auto-upload filled PDF back to Salesforce
API_PORT=8100                          # FastAPI server port
```

### Getting your Salesforce Security Token
1. Log into Salesforce
2. Click your avatar → **Settings**
3. **My Personal Information → Reset My Security Token**
4. Check your email — token will be sent there

---

## Project Structure

```
salesforce-pdf-filler/
├── README.md
├── run.py                   # CLI entry point (6 commands)
├── requirements.txt         # Python dependencies
├── .env.example             # Credentials template
├── .gitignore
├── CLAUDE.md                # AI coding rules
├── src/
│   ├── config.py            # Environment + paths
│   ├── salesforce_client.py # Salesforce API (connect, query, discover)
│   ├── pdf_filler.py        # PDF fill, flatten, validate
│   ├── field_mapper.py      # JSON config-driven mapping
│   ├── uploader.py          # Upload PDF back to Salesforce
│   ├── api.py               # FastAPI server (5 endpoints)
│   └── logger.py            # Run history (JSON + markdown)
├── n8n/
│   └── salesforce-pdf-filler-workflow.json  # Import into n8n
├── data/
│   └── field_map.json       # YOUR field mapping config
├── templates/               # Drop your PDF templates here
└── output/                  # Filled PDFs saved here
```

---

## Extending

### Add more Salesforce objects
Just add entries to `field_map.json`:
```json
{"sf_object": "Custom_Form__c", "sf_field": "Notes__c", "pdf_field": "additionalNotes", "type": "text"}
```

### Multiple PDF templates
```bash
python run.py fill --lead-id XYZ --template templates/intake_form.pdf
python run.py fill --lead-id XYZ --template templates/contract.pdf
```

### Upload filled PDF back to Salesforce
```bash
python run.py fill --lead-id XYZ --upload
```

### Use as a microservice
```bash
python run.py serve  # Runs on http://localhost:8100
# Now any system (n8n, Zapier, Make, custom app) can call the API
```

---

## Making It Live (Production Deployment)

Two clear paths. Pick one.

---

### Path A: Already Have n8n or Any VPS? Deploy on the Same Server ($0 Extra)

If you already have a server running n8n (or anything else), just add the API there. No extra cost.

**Step 1: SSH into your server and clone**
```bash
ssh root@your-server

git clone https://github.com/aiagentwithdhruv/salesforce-pdf-filler.git
cd salesforce-pdf-filler
pip install -r requirements.txt
```

**Step 2: Add your Salesforce credentials**
```bash
cp .env.example .env
nano .env
# Fill in: SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN
```

**Step 3: Drop your PDF template**
```bash
# Copy your fillable PDF to the templates folder
cp /path/to/your/form.pdf templates/
```

**Step 4: Discover PDF field names and set up mapping**
```bash
python run.py discover templates/form.pdf --save
# Edit data/field_map.json to map your Salesforce fields to the PDF field names
```

**Step 5: Set up as a system service (auto-starts on boot, auto-restarts on crash)**
```bash
sudo tee /etc/systemd/system/sf-pdf-filler.service << 'EOF'
[Unit]
Description=Salesforce PDF Filler API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/salesforce-pdf-filler
ExecStart=/usr/bin/python3 run.py serve
Restart=always
EnvironmentFile=/root/salesforce-pdf-filler/.env

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable sf-pdf-filler
sudo systemctl start sf-pdf-filler
```

**Step 6: Verify it's running**
```bash
curl http://localhost:8100/health
# Should return: {"status": "ok", "service": "salesforce-pdf-filler"}
```

**Step 7: Connect n8n**
- Open the n8n workflow (import `n8n/salesforce-pdf-filler-workflow.json`)
- The HTTP Request node already points to `http://localhost:8100` — no change needed since it's on the same server
- Add your Salesforce credentials in n8n
- Activate the workflow

**Done.** Every new Salesforce Lead auto-generates a filled PDF and emails it. Zero manual work.

---

### Path B: Don't Have a Server? Use Docker on a VPS ($4-6/mo)

Get a cheap VPS, deploy with Docker, done forever.

**Step 1: Get a VPS (pick one)**

| Provider | Cost | What You Get |
|----------|------|-------------|
| **Oracle Cloud Free Tier** | $0/mo forever | 4 cores, 24GB RAM (best free option) |
| **Hetzner CAX11** | ~$4/mo | 2 cores, 4GB RAM (best budget) |
| **DigitalOcean** | $6/mo | 1 core, 1GB RAM |

**Step 2: SSH in and deploy**
```bash
ssh root@your-new-server

# Install Docker (if not installed)
curl -fsSL https://get.docker.com | sh

# Clone the repo
git clone https://github.com/aiagentwithdhruv/salesforce-pdf-filler.git
cd salesforce-pdf-filler

# Add your credentials
cp .env.example .env
nano .env

# Drop your PDF template
cp /path/to/your/form.pdf templates/

# Build and run
docker build -t sf-pdf-filler .
docker run -d --name sf-pdf-filler \
  --env-file .env \
  -v $(pwd)/templates:/app/templates \
  -v $(pwd)/output:/app/output \
  -p 8100:8100 \
  --restart unless-stopped \
  sf-pdf-filler
```

**Step 3: Verify**
```bash
curl http://localhost:8100/health
```

**Step 4: Connect n8n**
- Update the HTTP Request node URL in the n8n workflow to `http://YOUR_SERVER_IP:8100/fill/raw`
- Add Salesforce credentials in n8n
- Activate

---

### Making It Fully Automated (Both Paths)

Once deployed, choose your automation trigger:

**Real-time (recommended):** Activate the n8n Salesforce Trigger → every new Lead auto-fills a PDF and emails it. Zero manual work.

**Scheduled batch:** Add a cron job to process all new leads daily:
```bash
crontab -e
# Every day at 9 AM
0 9 * * * cd /root/salesforce-pdf-filler && python run.py batch --since today
```

**On-demand:** Any system can POST to `http://your-server:8100/fill` and get a filled PDF back instantly

---

## Tech Stack

- **Python 3.11+**
- **simple-salesforce** — Salesforce REST API client
- **fillpdf** — PDF AcroForm filling
- **FastAPI + Uvicorn** — API server
- **Click** — CLI framework
- **n8n** — Visual workflow automation

---

## License

MIT

---

Built by [AIwithDhruv](https://github.com/aiagentwithdhruv)
