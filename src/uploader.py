"""
Uploader — attach filled PDFs back to Salesforce records.
Uses ContentVersion (modern Salesforce Files API).
"""

import base64
from pathlib import Path


class SalesforceUploader:
    def __init__(self, sf_client):
        """Takes a SalesforceClient instance."""
        self.sf = sf_client.sf

    def upload_to_record(self, record_id: str, pdf_path: str | Path, title: str | None = None) -> str:
        """
        Upload a PDF to Salesforce and attach it to a record.
        Uses ContentVersion (Salesforce Files) — works on all modern orgs.
        Returns the ContentVersion ID.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if title is None:
            title = pdf_path.stem

        # Read and base64 encode the PDF
        content_b64 = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")

        # Create ContentVersion (auto-creates ContentDocument)
        result = self.sf.ContentVersion.create({
            "Title": title,
            "PathOnClient": pdf_path.name,
            "VersionData": content_b64,
            "FirstPublishLocationId": record_id,  # Attaches to the record
        })

        return result["id"]

    def upload_as_attachment(self, record_id: str, pdf_path: str | Path, name: str | None = None) -> str:
        """
        Legacy upload using Attachment object (for older Salesforce orgs).
        Prefer upload_to_record() for modern orgs.
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        if name is None:
            name = pdf_path.name

        content_b64 = base64.b64encode(pdf_path.read_bytes()).decode("utf-8")

        result = self.sf.Attachment.create({
            "ParentId": record_id,
            "Name": name,
            "Body": content_b64,
            "ContentType": "application/pdf",
        })

        return result["id"]
