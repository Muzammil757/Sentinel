"""
The demo web UI is served as static files from this same FastAPI process
(see main.py) so the browser only ever talks to /api/* same-origin -- no
CORS, and no Supabase credential of any kind needs to reach client code.
These tests use the real on-disk frontend/ directory (not a fake), since the
whole point is confirming what actually gets served and what actually ships
in the frontend's source files.
"""

from pathlib import Path

import re

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"

SECRET_PATTERNS = [
    re.compile(r"SUPABASE_SERVICE_ROLE_KEY"),
    re.compile(r"SUPABASE_ANON_KEY"),
    re.compile(r"SUPABASE_URL\s*[:=]\s*['\"]https?://"),
    re.compile(r"https?://[a-z0-9]+\.supabase\.co"),
    re.compile(r"eyJ[A-Za-z0-9_-]{20,}"),  # JWT-shaped token
]


def test_root_serves_the_frontend_index(api_client):
    response = api_client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Sentinel" in response.text


def test_frontend_javascript_is_served(api_client):
    response = api_client.get("/app.js")
    assert response.status_code == 200
    assert "API_BASE" in response.text


def test_api_routes_take_precedence_over_the_static_mount(api_client):
    response = api_client.get("/api/cases")
    assert response.status_code == 200
    assert response.json() == []


def test_frontend_source_contains_no_supabase_credentials():
    assert FRONTEND_DIR.is_dir(), "frontend/ directory is expected to exist"
    checked_any = False
    for path in FRONTEND_DIR.rglob("*"):
        if path.suffix not in (".html", ".js", ".css"):
            continue
        checked_any = True
        text = path.read_text(encoding="utf-8")
        for pattern in SECRET_PATTERNS:
            assert not pattern.search(text), f"possible secret material found in {path}"
    assert checked_any, "expected at least one frontend source file to scan"
