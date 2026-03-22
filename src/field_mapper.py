"""
Field Mapper — maps Salesforce fields to PDF field names using JSON config.
Handles multi-object merging, type conversion, defaults.
"""

import json
from pathlib import Path
from datetime import datetime
from src.config import app_config, FIELD_MAP_PATH


class FieldMapper:
    def __init__(self, config_path: str | Path | None = None):
        self.config_path = Path(config_path or FIELD_MAP_PATH)
        self.config = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {"mappings": [], "defaults": {}}
        return json.loads(self.config_path.read_text())

    def reload(self):
        """Reload config from disk (useful after editing field_map.json)."""
        self.config = self._load_config()

    def merge_and_map(self, **sf_objects: dict) -> dict:
        """
        Merge multiple Salesforce objects into a flat dict matching PDF field names.

        Usage:
            mapper.merge_and_map(
                Lead=lead_record,
                Contact=contact_record,
                Opportunity=opp_record,
                Custom_Form__c=custom_record,
            )
        """
        pdf_data = {}
        defaults = self.config.get("defaults", {})
        empty_value = defaults.get("emptyValue", "")

        for mapping in self.config.get("mappings", []):
            sf_object = mapping["sf_object"]
            sf_field = mapping["sf_field"]
            pdf_field = mapping["pdf_field"]
            field_type = mapping.get("type", "text")

            # Get the source record
            record = sf_objects.get(sf_object, {})
            raw_value = self._get_nested_value(record, sf_field)

            # Convert value based on type
            pdf_data[pdf_field] = self._convert_value(raw_value, field_type, defaults, empty_value)

        return pdf_data

    def _get_nested_value(self, record: dict, field_path: str):
        """Support nested fields like 'Account.Name'."""
        parts = field_path.split(".")
        current = record
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    def _convert_value(self, value, field_type: str, defaults: dict, empty_value: str) -> str:
        """Convert Salesforce value to PDF-compatible string."""
        if value is None:
            return empty_value

        if field_type == "checkbox":
            truthy = str(value).lower() in ("true", "1", "yes")
            return defaults.get("checkboxTrue", app_config.CHECKBOX_TRUE) if truthy else defaults.get("checkboxFalse", app_config.CHECKBOX_FALSE)

        if field_type == "date":
            try:
                dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                fmt = defaults.get("dateFormat", app_config.DATE_FORMAT)
                # Convert Python format if needed
                fmt = fmt.replace("YYYY", "%Y").replace("MM", "%m").replace("DD", "%d")
                return dt.strftime(fmt)
            except (ValueError, TypeError):
                return str(value)

        if field_type == "currency":
            try:
                return f"${float(value):,.2f}"
            except (ValueError, TypeError):
                return str(value)

        return str(value)

    def generate_template_config(self, pdf_fields: dict, sf_fields: dict[str, list[dict]]) -> dict:
        """
        Auto-generate a field_map.json by fuzzy-matching PDF field names
        to Salesforce field labels. Returns suggested mapping for review.
        """
        suggestions = []

        for pdf_field_name in pdf_fields:
            best_match = None
            best_score = 0
            pdf_lower = pdf_field_name.lower().replace("_", " ").replace("-", " ")

            for obj_name, fields in sf_fields.items():
                for field in fields:
                    sf_lower = field["label"].lower()
                    # Simple overlap scoring
                    score = len(set(pdf_lower.split()) & set(sf_lower.split()))
                    if score > best_score:
                        best_score = score
                        best_match = {"sf_object": obj_name, "sf_field": field["name"], "sf_label": field["label"]}

            suggestions.append({
                "pdf_field": pdf_field_name,
                "suggested_sf_object": best_match["sf_object"] if best_match and best_score > 0 else "UNMAPPED",
                "suggested_sf_field": best_match["sf_field"] if best_match and best_score > 0 else "UNMAPPED",
                "confidence": "high" if best_score >= 2 else "low" if best_score == 1 else "none",
            })

        return {"mappings": suggestions, "defaults": {"dateFormat": "YYYY-MM-DD", "emptyValue": "", "checkboxTrue": "Yes", "checkboxFalse": "Off"}}

    def save_config(self, config: dict | None = None):
        """Save config to disk."""
        config = config or self.config
        self.config_path.write_text(json.dumps(config, indent=2))
