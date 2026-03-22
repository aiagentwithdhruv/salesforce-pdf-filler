"""
Salesforce API client — connect, query any object, discover fields.
"""

from simple_salesforce import Salesforce, SalesforceAuthenticationFailed
from src.config import sf_config


class SalesforceClient:
    def __init__(self):
        self.sf = None
        self._connect()

    def _connect(self):
        try:
            self.sf = Salesforce(
                username=sf_config.USERNAME,
                password=sf_config.PASSWORD,
                security_token=sf_config.SECURITY_TOKEN,
                domain=sf_config.DOMAIN,
                version=sf_config.API_VERSION,
            )
        except SalesforceAuthenticationFailed as e:
            raise ConnectionError(
                f"Salesforce auth failed. Check SF_USERNAME, SF_PASSWORD, SF_SECURITY_TOKEN in .env\n{e}"
            )

    # ── Query helpers ──────────────────────────────────────────────

    def query(self, soql: str) -> list[dict]:
        """Run SOQL query, return all records (auto-paginate)."""
        result = self.sf.query_all(soql)
        return result.get("records", [])

    def get_record(self, object_name: str, record_id: str, fields: list[str] | None = None) -> dict:
        """Get a single record by ID."""
        obj = getattr(self.sf, object_name)
        if fields:
            soql = f"SELECT {', '.join(fields)} FROM {object_name} WHERE Id = '{record_id}'"
            records = self.query(soql)
            return records[0] if records else {}
        return obj.get(record_id)

    def get_lead(self, lead_id: str, fields: list[str] | None = None) -> dict:
        """Get a Lead by ID."""
        return self.get_record("Lead", lead_id, fields)

    def get_contact(self, contact_id: str, fields: list[str] | None = None) -> dict:
        """Get a Contact by ID."""
        return self.get_record("Contact", contact_id, fields)

    def get_opportunity(self, opp_id: str, fields: list[str] | None = None) -> dict:
        """Get an Opportunity by ID."""
        return self.get_record("Opportunity", opp_id, fields)

    def get_account(self, account_id: str, fields: list[str] | None = None) -> dict:
        """Get an Account by ID."""
        return self.get_record("Account", account_id, fields)

    def query_custom(self, soql: str) -> list[dict]:
        """Query any custom object via raw SOQL."""
        return self.query(soql)

    # ── Discovery ──────────────────────────────────────────────────

    def list_objects(self) -> list[str]:
        """List all object names in the org."""
        desc = self.sf.describe()
        return sorted([obj["name"] for obj in desc["sobjects"]])

    def list_fields(self, object_name: str) -> list[dict]:
        """List all fields for an object with name, label, type."""
        obj = getattr(self.sf, object_name)
        desc = obj.describe()
        return [
            {
                "name": f["name"],
                "label": f["label"],
                "type": f["type"],
                "required": not f["nillable"] and not f["defaultedOnCreate"],
            }
            for f in desc["fields"]
        ]

    def get_recent(self, object_name: str, limit: int = 10, fields: list[str] | None = None) -> list[dict]:
        """Get recent records from any object."""
        if not fields:
            fields = ["Id", "Name", "CreatedDate"]
        field_str = ", ".join(fields)
        soql = f"SELECT {field_str} FROM {object_name} ORDER BY CreatedDate DESC LIMIT {limit}"
        return self.query(soql)

    def get_leads_since(self, since_date: str, fields: list[str] | None = None) -> list[dict]:
        """Get all Leads created since a date (YYYY-MM-DD)."""
        if not fields:
            fields = ["Id", "FirstName", "LastName", "Email", "Phone", "Company", "CreatedDate"]
        field_str = ", ".join(fields)
        soql = f"SELECT {field_str} FROM Lead WHERE CreatedDate >= {since_date}T00:00:00Z ORDER BY CreatedDate DESC"
        return self.query(soql)
