"""
Configuration for PDF Search.
Override any setting with environment variables.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).absolute().parent

# Directory containing PDFs to index
PDF_DIR = Path(os.environ.get("PDF_SEARCH_PDF_DIR", os.path.join(BASE_DIR, "pdfs")))

# Database file
DB_PATH = Path(os.environ.get("PDF_SEARCH_DB", os.path.join(BASE_DIR, "pdf_search.db")))

# Web server
HOST = os.environ.get("PDF_SEARCH_HOST", "0.0.0.0")
PORT = int(os.environ.get("PDF_SEARCH_PORT", "5555"))

# Site title (shown in the web UI)
SITE_TITLE = os.environ.get("PDF_SEARCH_TITLE", "PDF Search")

# Extractor workers (parallel PDF processing)
MAX_WORKERS = int(os.environ.get("PDF_SEARCH_MAX_WORKERS", "3"))
