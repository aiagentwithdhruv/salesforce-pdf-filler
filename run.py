#!/usr/bin/env python3
"""
Salesforce PDF Filler — CLI Entry Point

Commands:
  discover  — Show all form fields in a PDF template
  fill      — Fill a PDF with data from a Salesforce record
  batch     — Fill PDFs for all records matching a query
  suggest   — Auto-suggest field mapping between SF and PDF
  stats     — Show run statistics
  serve     — Start the FastAPI server (for n8n integration)
"""

import json
import sys
from pathlib import Path

import click

from src.config import TEMPLATES_DIR, OUTPUT_DIR, FIELD_MAP_PATH, app_config


@click.group()
def cli():
    """Salesforce Multi-Form to Fillable PDF Automation."""
    pass


# ── Discover PDF Fields ──────────────────────────────────────────

@cli.command()
@click.argument("template_path", type=click.Path(exists=True))
@click.option("--save", is_flag=True, help="Save field report to data/pdf_fields_report.json")
def discover(template_path: str, save: bool):
    """Discover all form fields in a PDF template."""
    from src.pdf_filler import PDFFiller

    filler = PDFFiller(template_path)
    fields = filler.discover_fields_detailed()

    click.echo(f"\n{'='*60}")
    click.echo(f"  PDF Form Fields — {Path(template_path).name}")
    click.echo(f"  Total fields: {len(fields)}")
    click.echo(f"{'='*60}\n")

    for f in fields:
        icon = "[x]" if f["type"] == "checkbox" else "[T]"
        current = f" (current: {f['current_value']})" if f["current_value"] else ""
        click.echo(f"  {icon}  {f['field_name']}{current}")

    if save:
        report_path = filler.save_field_report()
        click.echo(f"\nReport saved: {report_path}")

    click.echo(f"\nUse these field names in data/field_map.json to map Salesforce fields.\n")


# ── Fill Single Record ──────────────────────────────────────────

@cli.command()
@click.option("--lead-id", help="Salesforce Lead ID")
@click.option("--contact-id", help="Salesforce Contact ID")
@click.option("--opp-id", help="Salesforce Opportunity ID")
@click.option("--custom-soql", help="Custom SOQL query for additional data")
@click.option("--template", default=None, help="PDF template path (default: first .pdf in templates/)")
@click.option("--output", default=None, help="Output path (default: output/filled_<id>.pdf)")
@click.option("--no-flatten", is_flag=True, help="Don't flatten the PDF (keep editable)")
@click.option("--upload", is_flag=True, help="Upload filled PDF back to Salesforce")
@click.option("--dry-run", is_flag=True, help="Show what would be filled without writing PDF")
def fill(lead_id, contact_id, opp_id, custom_soql, template, output, no_flatten, upload, dry_run):
    """Fill a PDF with Salesforce record data."""
    from src.salesforce_client import SalesforceClient
    from src.pdf_filler import PDFFiller
    from src.field_mapper import FieldMapper
    from src.uploader import SalesforceUploader
    from src import logger

    if not any([lead_id, contact_id, opp_id, custom_soql]):
        click.echo("Error: Provide at least one of --lead-id, --contact-id, --opp-id, or --custom-soql")
        sys.exit(1)

    # Connect to Salesforce
    click.echo("Connecting to Salesforce...")
    sf = SalesforceClient()

    # Fetch records
    sf_objects = {}
    primary_id = ""

    if lead_id:
        click.echo(f"  Fetching Lead {lead_id}...")
        sf_objects["Lead"] = sf.get_lead(lead_id)
        primary_id = lead_id

    if contact_id:
        click.echo(f"  Fetching Contact {contact_id}...")
        sf_objects["Contact"] = sf.get_contact(contact_id)
        primary_id = primary_id or contact_id

    if opp_id:
        click.echo(f"  Fetching Opportunity {opp_id}...")
        sf_objects["Opportunity"] = sf.get_opportunity(opp_id)
        primary_id = primary_id or opp_id

    if custom_soql:
        click.echo(f"  Running custom query...")
        results = sf.query_custom(custom_soql)
        if results:
            # Use the object name from SOQL (best effort)
            obj_name = custom_soql.split("FROM")[1].split()[0].strip() if "FROM" in custom_soql else "Custom"
            sf_objects[obj_name] = results[0]
            primary_id = primary_id or results[0].get("Id", "custom")

    # Map fields
    click.echo("Mapping fields...")
    mapper = FieldMapper()
    pdf_data = mapper.merge_and_map(**sf_objects)

    if dry_run:
        click.echo(f"\n{'='*60}")
        click.echo("  DRY RUN — Data that would be filled:")
        click.echo(f"{'='*60}")
        for k, v in pdf_data.items():
            click.echo(f"  {k}: {v}")
        click.echo(f"\nTotal fields: {len(pdf_data)}")
        return

    # Resolve template
    if template is None:
        templates = list(TEMPLATES_DIR.glob("*.pdf"))
        if not templates:
            click.echo(f"Error: No PDF templates found in {TEMPLATES_DIR}")
            sys.exit(1)
        template = str(templates[0])
        click.echo(f"  Using template: {Path(template).name}")

    # Fill PDF
    click.echo("Filling PDF...")
    filler = PDFFiller(template)

    if output is None:
        output = OUTPUT_DIR / f"filled_{primary_id}.pdf"

    filled_path = filler.fill(pdf_data, output, flatten=not no_flatten)

    # Validate coverage
    validation = filler.validate_mapping(pdf_data)
    click.echo(f"  Coverage: {validation['coverage_pct']}% ({len(validation['matched'])}/{validation['total_pdf_fields']} fields)")

    if validation["unmapped_pdf_fields"]:
        click.echo(f"  Unmapped PDF fields: {', '.join(validation['unmapped_pdf_fields'][:5])}")

    # Upload if requested
    if upload:
        click.echo("Uploading to Salesforce...")
        uploader = SalesforceUploader(sf)
        cv_id = uploader.upload_to_record(primary_id, filled_path)
        click.echo(f"  Uploaded as ContentVersion: {cv_id}")

    # Log
    logger.log_run(
        record_id=primary_id,
        sf_object=list(sf_objects.keys())[0] if sf_objects else "unknown",
        template=Path(template).name,
        output=str(filled_path),
        fields_filled=len(validation["matched"]),
        coverage_pct=validation["coverage_pct"],
    )

    click.echo(f"\nDone! Output: {filled_path}")


# ── Batch Fill ──────────────────────────────────────────────────

@cli.command()
@click.option("--since", default="today", help="Fill PDFs for leads created since date (YYYY-MM-DD or 'today')")
@click.option("--template", default=None, help="PDF template path")
@click.option("--upload", is_flag=True, help="Upload each filled PDF back to Salesforce")
@click.option("--limit", default=50, help="Max records to process")
def batch(since, template, upload, limit):
    """Batch fill PDFs for multiple Salesforce records."""
    from datetime import date
    from src.salesforce_client import SalesforceClient
    from src.pdf_filler import PDFFiller
    from src.field_mapper import FieldMapper
    from src.uploader import SalesforceUploader
    from src import logger

    if since == "today":
        since = date.today().isoformat()

    # Connect
    click.echo("Connecting to Salesforce...")
    sf = SalesforceClient()

    # Fetch leads
    click.echo(f"Fetching Leads since {since}...")
    leads = sf.get_leads_since(since)[:limit]
    click.echo(f"  Found {len(leads)} leads")

    if not leads:
        click.echo("No leads found. Nothing to do.")
        return

    # Resolve template
    if template is None:
        templates = list(TEMPLATES_DIR.glob("*.pdf"))
        if not templates:
            click.echo(f"Error: No PDF templates in {TEMPLATES_DIR}")
            sys.exit(1)
        template = str(templates[0])

    mapper = FieldMapper()
    filler = PDFFiller(template)
    uploader = SalesforceUploader(sf) if upload else None

    success = 0
    for i, lead in enumerate(leads):
        lead_id = lead.get("Id", f"unknown_{i}")
        click.echo(f"\n[{i+1}/{len(leads)}] Processing Lead {lead_id}...")

        try:
            pdf_data = mapper.merge_and_map(Lead=lead)
            out_path = OUTPUT_DIR / "batch" / f"filled_{lead_id}.pdf"
            out_path.parent.mkdir(parents=True, exist_ok=True)

            filled = filler.fill(pdf_data, out_path)

            if uploader:
                uploader.upload_to_record(lead_id, filled)
                click.echo(f"  Uploaded to Salesforce")

            logger.log_run(
                record_id=lead_id, sf_object="Lead",
                template=Path(template).name, output=str(filled),
            )
            success += 1

        except Exception as e:
            click.echo(f"  Error: {e}")
            logger.log_run(
                record_id=lead_id, sf_object="Lead",
                template=Path(template).name, output="",
                status="error", error=str(e),
            )

    click.echo(f"\nBatch complete: {success}/{len(leads)} successful")


# ── Auto-Suggest Mapping ────────────────────────────────────────

@cli.command()
@click.argument("template_path", type=click.Path(exists=True))
@click.option("--objects", default="Lead", help="Comma-separated SF objects to match against")
@click.option("--save", is_flag=True, help="Save suggested mapping to field_map.json")
def suggest(template_path, objects, save):
    """Auto-suggest field mapping between Salesforce and PDF."""
    from src.salesforce_client import SalesforceClient
    from src.pdf_filler import PDFFiller
    from src.field_mapper import FieldMapper

    click.echo("Connecting to Salesforce...")
    sf = SalesforceClient()

    click.echo("Discovering PDF fields...")
    filler = PDFFiller(template_path)
    pdf_fields = filler.discover_fields()

    click.echo("Fetching Salesforce field metadata...")
    sf_fields = {}
    for obj_name in objects.split(","):
        obj_name = obj_name.strip()
        click.echo(f"  {obj_name}...")
        sf_fields[obj_name] = sf.list_fields(obj_name)

    mapper = FieldMapper()
    suggested = mapper.generate_template_config(pdf_fields, sf_fields)

    click.echo(f"\n{'='*60}")
    click.echo("  Suggested Field Mapping")
    click.echo(f"{'='*60}\n")

    for m in suggested["mappings"]:
        confidence_icon = {"high": "+", "low": "?", "none": "x"}[m["confidence"]]
        click.echo(f"  [{confidence_icon}] {m['pdf_field']}  <-  {m['suggested_sf_object']}.{m['suggested_sf_field']}")

    if save:
        # Convert to final format
        final_mappings = [
            {"sf_object": m["suggested_sf_object"], "sf_field": m["suggested_sf_field"], "pdf_field": m["pdf_field"]}
            for m in suggested["mappings"]
            if m["confidence"] != "none"
        ]
        final_config = {"mappings": final_mappings, "defaults": suggested["defaults"]}
        mapper.config = final_config
        mapper.save_config()
        click.echo(f"\nSaved to {FIELD_MAP_PATH}")
    else:
        click.echo(f"\nRun with --save to write to {FIELD_MAP_PATH}")


# ── Stats ───────────────────────────────────────────────────────

@cli.command()
def stats():
    """Show run statistics."""
    from src import logger

    s = logger.get_stats()
    click.echo(f"\n{'='*40}")
    click.echo(f"  Salesforce PDF Filler — Stats")
    click.echo(f"{'='*40}")
    click.echo(f"  Total runs:    {s['total_runs']}")
    click.echo(f"  Successful:    {s['successful']}")
    click.echo(f"  Failed:        {s['failed']}")
    click.echo(f"  Success rate:  {s['success_rate']}%")
    click.echo(f"  Last run:      {s['last_run'] or 'Never'}")
    click.echo()


# ── Serve (FastAPI) ─────────────────────────────────────────────

@cli.command()
@click.option("--host", default=None, help="Host (default: 0.0.0.0)")
@click.option("--port", default=None, type=int, help="Port (default: 8100)")
def serve(host, port):
    """Start the FastAPI server for n8n / external integrations."""
    import uvicorn
    from src.api import app as api_app

    host = host or app_config.API_HOST
    port = port or app_config.API_PORT

    click.echo(f"\nStarting API server on http://{host}:{port}")
    click.echo("Endpoints:")
    click.echo("  POST /fill          — Fill a PDF from Salesforce data")
    click.echo("  POST /fill/raw      — Fill a PDF from raw JSON data")
    click.echo("  GET  /discover      — List PDF template fields")
    click.echo("  GET  /health        — Health check")
    click.echo("  GET  /stats         — Run statistics\n")

    uvicorn.run(api_app, host=host, port=port)


if __name__ == "__main__":
    cli()
