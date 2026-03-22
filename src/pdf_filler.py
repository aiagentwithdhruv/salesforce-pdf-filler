"""
PDF form filler — discover fields, fill, flatten.
Uses fillpdf for AcroForm PDFs.
"""

import json
from pathlib import Path
from fillpdf import fillpdfs
from src.config import app_config, OUTPUT_DIR


class PDFFiller:
    def __init__(self, template_path: str | Path):
        self.template_path = str(template_path)
        self._fields: dict = {}

    def discover_fields(self) -> dict:
        """
        Extract all form field names from the PDF template.
        Run this FIRST with any new template to know what fields exist.
        Returns dict of {field_name: current_value}.
        """
        self._fields = fillpdfs.get_form_fields(self.template_path)
        return self._fields

    def discover_fields_detailed(self) -> list[dict]:
        """Return fields with more detail for mapping."""
        raw = self.discover_fields()
        return [
            {"field_name": k, "current_value": v, "type": "checkbox" if v in ("Off", "Yes", "/Off", "/Yes") else "text"}
            for k, v in raw.items()
        ]

    def fill(self, data: dict, output_path: str | Path | None = None, flatten: bool | None = None) -> Path:
        """
        Fill PDF template with data dict.
        Keys must match PDF field names exactly (case-sensitive).
        """
        if output_path is None:
            output_path = OUTPUT_DIR / "filled_output.pdf"
        output_path = Path(output_path)

        should_flatten = flatten if flatten is not None else app_config.FLATTEN_OUTPUT

        # Fill the PDF
        fillpdfs.write_fillable_pdf(self.template_path, str(output_path), data)

        # Flatten if requested (makes non-editable, required for archival)
        if should_flatten:
            flat_path = output_path.with_stem(output_path.stem + "_flat")
            fillpdfs.flatten_pdf(str(output_path), str(flat_path), as_images=False)
            return flat_path

        return output_path

    def fill_batch(self, records: list[dict], output_dir: str | Path | None = None) -> list[Path]:
        """Fill PDF for multiple records. Returns list of output paths."""
        if output_dir is None:
            output_dir = OUTPUT_DIR / "batch"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        for i, record in enumerate(records):
            record_id = record.get("_record_id", f"record_{i}")
            out_path = output_dir / f"filled_{record_id}.pdf"
            filled = self.fill(record, out_path)
            results.append(filled)

        return results

    def validate_mapping(self, data: dict) -> dict:
        """
        Check which data keys match PDF fields and which don't.
        Helps debug field mapping issues.
        """
        if not self._fields:
            self.discover_fields()

        pdf_keys = set(self._fields.keys())
        data_keys = set(data.keys())

        return {
            "matched": sorted(pdf_keys & data_keys),
            "unmapped_pdf_fields": sorted(pdf_keys - data_keys),
            "unmapped_data_keys": sorted(data_keys - pdf_keys),
            "total_pdf_fields": len(pdf_keys),
            "total_data_keys": len(data_keys),
            "coverage_pct": round(len(pdf_keys & data_keys) / max(len(pdf_keys), 1) * 100, 1),
        }

    def save_field_report(self, output_path: str | Path | None = None) -> Path:
        """Save discovered fields to JSON for reference."""
        if not self._fields:
            self.discover_fields()

        if output_path is None:
            output_path = OUTPUT_DIR / "pdf_fields_report.json"

        report = self.discover_fields_detailed()
        Path(output_path).write_text(json.dumps(report, indent=2))
        return Path(output_path)
