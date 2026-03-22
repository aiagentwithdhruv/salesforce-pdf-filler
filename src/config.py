"""
Configuration — loads env vars, paths, constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"
DATA_DIR = BASE_DIR / "data"
FIELD_MAP_PATH = DATA_DIR / "field_map.json"

# Ensure dirs exist
OUTPUT_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)


class SalesforceConfig:
    USERNAME = os.getenv("SF_USERNAME", "")
    PASSWORD = os.getenv("SF_PASSWORD", "")
    SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN", "")
    DOMAIN = os.getenv("SF_DOMAIN", "login")  # "login" for prod, "test" for sandbox
    API_VERSION = os.getenv("SF_API_VERSION", "59.0")


class AppConfig:
    # PDF
    FLATTEN_OUTPUT = os.getenv("FLATTEN_PDF", "true").lower() == "true"
    DATE_FORMAT = os.getenv("DATE_FORMAT", "%Y-%m-%d")
    CHECKBOX_TRUE = "Yes"
    CHECKBOX_FALSE = "Off"

    # Upload
    UPLOAD_TO_SF = os.getenv("UPLOAD_TO_SF", "false").lower() == "true"
    EMAIL_FILLED_PDF = os.getenv("EMAIL_FILLED_PDF", "false").lower() == "true"

    # API Server
    API_HOST = os.getenv("API_HOST", "0.0.0.0")
    API_PORT = int(os.getenv("API_PORT", "8100"))


sf_config = SalesforceConfig()
app_config = AppConfig()
