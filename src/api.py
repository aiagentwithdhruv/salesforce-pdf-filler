"""
FastAPI wrapper — exposes the PDF filler as an API for n8n and external integrations.

Endpoints:
  POST /fill          — Fill PDF from Salesforce record IDs
  POST /fill/raw      — Fill PDF from raw JSON data (no Salesforce needed)
  GET  /discover      — List all form fields in a PDF template
  GET  /health        — Health check
  GET  /stats         — Run statistics
  POST /suggest       — Auto-suggest field mapping
"""

import io
import base64
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.config import TEMPLATES_DIR, OUTPUT_DIR
from src.pdf_filler import PDFFiller
from src.field_mapper import FieldMapper
from src import logger as run_logger


app = FastAPI(
    title="Salesforce PDF Filler API",
    description="Fill PDF forms with Salesforce data. Built for n8n integration.",
    version="1.0.0",
)


# ── Models ───────────────────────────────────────────────────────

class FillRequest(BaseModel):
    lead_id: str | None = Field(None, description="Salesforce Lead ID")
    contact_id: str | None = Field(None, description="Salesforce Contact ID")
    opp_id: str | None = Field(None, description="Salesforce Opportunity ID")
    custom_soql: str | None = Field(None, description="Custom SOQL for additional data")
    template_name: str | None = Field(None, description="PDF template filename in templates/")
    upload_to_sf: bool = Field(False, description="Upload filled PDF back to Salesforce")
    return_base64: bool = Field(True, description="Return PDF as base64 (for n8n) vs file download")


class RawFillRequest(BaseModel):
    data: dict = Field(..., description="Key-value pairs matching PDF field names")
    template_name: str | None = Field(None, description="PDF template filename")
    return_base64: bool = Field(True, description="Return as base64 string")


class SuggestRequest(BaseModel):
    template_name: str = Field(..., description="PDF template filename")
    sf_objects: list[str] = Field(default=["Lead"], description="Salesforce objects to match against")


# ── Helpers ──────────────────────────────────────────────────────

def _resolve_template(template_name: str | None) -> Path:
    if template_name:
        path = TEMPLATES_DIR / template_name
        if not path.exists():
            raise HTTPException(404, f"Template '{template_name}' not found in templates/")
        return path

    templates = list(TEMPLATES_DIR.glob("*.pdf"))
    if not templates:
        raise HTTPException(404, "No PDF templates found in templates/ folder")
    return templates[0]


# ── Endpoints ────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "salesforce-pdf-filler", "version": "1.0.0"}


@app.get("/stats")
def stats():
    return run_logger.get_stats()


@app.get("/discover")
def discover(template_name: str | None = None):
    """List all form fields in a PDF template."""
    template = _resolve_template(template_name)
    filler = PDFFiller(template)
    fields = filler.discover_fields_detailed()
    return {
        "template": template.name,
        "total_fields": len(fields),
        "fields": fields,
    }


@app.post("/fill")
def fill_from_salesforce(req: FillRequest):
    """Fill a PDF with data from Salesforce records."""
    from src.salesforce_client import SalesforceClient
    from src.uploader import SalesforceUploader

    if not any([req.lead_id, req.contact_id, req.opp_id, req.custom_soql]):
        raise HTTPException(400, "Provide at least one of: lead_id, contact_id, opp_id, custom_soql")

    # Connect and fetch
    sf = SalesforceClient()
    sf_objects = {}
    primary_id = ""

    if req.lead_id:
        sf_objects["Lead"] = sf.get_lead(req.lead_id)
        primary_id = req.lead_id

    if req.contact_id:
        sf_objects["Contact"] = sf.get_contact(req.contact_id)
        primary_id = primary_id or req.contact_id

    if req.opp_id:
        sf_objects["Opportunity"] = sf.get_opportunity(req.opp_id)
        primary_id = primary_id or req.opp_id

    if req.custom_soql:
        results = sf.query_custom(req.custom_soql)
        if results:
            obj_name = req.custom_soql.split("FROM")[1].split()[0].strip() if "FROM" in req.custom_soql else "Custom"
            sf_objects[obj_name] = results[0]
            primary_id = primary_id or results[0].get("Id", "custom")

    # Map and fill
    mapper = FieldMapper()
    pdf_data = mapper.merge_and_map(**sf_objects)

    template = _resolve_template(req.template_name)
    filler = PDFFiller(template)

    out_path = OUTPUT_DIR / f"filled_{primary_id}.pdf"
    filled_path = filler.fill(pdf_data, out_path)

    validation = filler.validate_mapping(pdf_data)

    # Upload if requested
    upload_id = None
    if req.upload_to_sf:
        uploader = SalesforceUploader(sf)
        upload_id = uploader.upload_to_record(primary_id, filled_path)

    # Log
    run_logger.log_run(
        record_id=primary_id,
        sf_object=list(sf_objects.keys())[0],
        template=template.name,
        output=str(filled_path),
        fields_filled=len(validation["matched"]),
        coverage_pct=validation["coverage_pct"],
    )

    # Return
    if req.return_base64:
        pdf_bytes = Path(filled_path).read_bytes()
        return {
            "status": "success",
            "record_id": primary_id,
            "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
            "filename": filled_path.name,
            "coverage": validation,
            "uploaded_to_sf": upload_id,
        }
    else:
        return StreamingResponse(
            io.BytesIO(Path(filled_path).read_bytes()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=filled_{primary_id}.pdf"},
        )


@app.post("/fill/raw")
def fill_from_raw(req: RawFillRequest):
    """
    Fill a PDF with raw JSON data — no Salesforce connection needed.
    Keys must match PDF form field names exactly.
    Perfect for n8n Code nodes that already have the data.
    """
    template = _resolve_template(req.template_name)
    filler = PDFFiller(template)

    out_path = OUTPUT_DIR / "filled_raw.pdf"
    filled_path = filler.fill(req.data, out_path)

    validation = filler.validate_mapping(req.data)

    run_logger.log_run(
        record_id="raw",
        sf_object="raw",
        template=template.name,
        output=str(filled_path),
        fields_filled=len(validation["matched"]),
        coverage_pct=validation["coverage_pct"],
    )

    if req.return_base64:
        pdf_bytes = Path(filled_path).read_bytes()
        return {
            "status": "success",
            "pdf_base64": base64.b64encode(pdf_bytes).decode("utf-8"),
            "filename": filled_path.name,
            "coverage": validation,
        }
    else:
        return StreamingResponse(
            io.BytesIO(Path(filled_path).read_bytes()),
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=filled_raw.pdf"},
        )


@app.post("/suggest")
def suggest_mapping(req: SuggestRequest):
    """Auto-suggest field mapping between Salesforce fields and PDF fields."""
    from src.salesforce_client import SalesforceClient

    template = _resolve_template(req.template_name)
    filler = PDFFiller(template)
    pdf_fields = filler.discover_fields()

    sf = SalesforceClient()
    sf_fields = {}
    for obj_name in req.sf_objects:
        sf_fields[obj_name] = sf.list_fields(obj_name)

    mapper = FieldMapper()
    suggested = mapper.generate_template_config(pdf_fields, sf_fields)

    return {
        "template": template.name,
        "suggested_mappings": suggested["mappings"],
        "defaults": suggested["defaults"],
    }
