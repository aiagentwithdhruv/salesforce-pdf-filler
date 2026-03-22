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

## Making It Live (Deployment)

Once you've tested locally and it works, here's how to deploy the FastAPI server so it runs 24/7 and n8n (or any system) can call it automatically.

### Option 1: Railway (Recommended for POC) — Free → $5/mo

Easiest deployment. Free tier includes 500 hours/month.

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and deploy
railway login
railway init
railway up

# 3. Set environment variables in Railway dashboard
# Add all vars from .env.example

# 4. Your API is live at: https://your-app.up.railway.app
# Update n8n HTTP Request node URL to this
```

**Cost:** Free tier (500 hrs/mo) → $5/mo for always-on
**Pros:** Zero config, auto-deploys on git push, free SSL

---

### Option 2: Render — Free (spins down after inactivity)

```bash
# 1. Create render.yaml in project root
cat > render.yaml << 'EOF'
services:
  - type: web
    name: salesforce-pdf-filler
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python run.py serve --host 0.0.0.0 --port $PORT
    envVars:
      - key: SF_USERNAME
        sync: false
      - key: SF_PASSWORD
        sync: false
      - key: SF_SECURITY_TOKEN
        sync: false
EOF

# 2. Connect GitHub repo on render.com → auto-deploys
```

**Cost:** Free (sleeps after 15 min inactivity, ~30s cold start) → $7/mo for always-on
**Pros:** Free tier, auto-deploy from GitHub

---

### Option 3: Docker on Any VPS — $4-6/mo (Always On, Full Control)

Best for production. Works on Hetzner, DigitalOcean, Oracle Free Tier, any VPS.

```dockerfile
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8100
CMD ["python", "run.py", "serve", "--host", "0.0.0.0", "--port", "8100"]
```

```bash
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

| VPS Provider | Cost | Notes |
|-------------|------|-------|
| **Oracle Cloud Free** | $0/mo forever | 4 ARM cores, 24GB RAM — best free option |
| **Hetzner CAX11** | €3.79/mo (~$4) | 2 ARM cores, 4GB RAM — best budget |
| **DigitalOcean** | $6/mo | 1 vCPU, 1GB RAM |
| **AWS Lightsail** | $3.50/mo | 512MB RAM — tight but works |

---

### Option 4: Modal (Serverless) — Free Tier

Pay only when the API is actually called. Perfect if usage is sporadic.

```bash
pip install modal
modal setup

# Deploy as serverless function
modal deploy src/api.py
```

**Cost:** Free tier (30 hrs/mo compute) → pay-per-request after
**Pros:** Zero cost when idle, auto-scales

---

### Option 5: Run on Same VPS as n8n

If you already have n8n self-hosted, just run the API on the same server:

```bash
# SSH into your n8n server
ssh root@your-server

# Clone and setup
git clone https://github.com/aiagentwithdhruv/salesforce-pdf-filler.git
cd salesforce-pdf-filler
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials

# Run with systemd (auto-restart, starts on boot)
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

# Now the API runs at http://localhost:8100 on the same server
# n8n can call it directly — no external URL needed!
```

**Cost:** $0 extra (uses your existing server)
**Best option if you already have a VPS**

---

### Automation: Making It Fully Hands-Off

Once deployed, set up automation so PDFs are generated without any manual work:

**Event-driven (real-time):**
- n8n Salesforce Trigger → fires on every new Lead → calls API → fills PDF → emails it
- Zero manual intervention. Activate the n8n workflow and forget.

**Scheduled (batch):**
```bash
# Add to crontab — fill PDFs for all new leads every day at 9 AM
crontab -e
0 9 * * * cd /path/to/salesforce-pdf-filler && python run.py batch --since today
```

**Webhook (on-demand):**
- The FastAPI server IS the webhook. Any system can POST to `/fill` and get a filled PDF back.
- Salesforce can call it directly via Outbound Messages or Platform Events.

### Recommended Setup

| Scenario | Deploy | Trigger | Cost |
|----------|--------|---------|------|
| **Quick POC / Demo** | Railway free | Manual / CLI | $0 |
| **Low volume (< 50 PDFs/day)** | Render free + n8n workflow | Salesforce Trigger | $0 |
| **Production (always on)** | Docker on VPS + n8n | Salesforce Trigger | $4-6/mo |
| **Already have n8n VPS** | Same server (systemd) | Salesforce Trigger | $0 extra |
| **Enterprise / high volume** | Docker + load balancer | SF Platform Events | $10-20/mo |

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
