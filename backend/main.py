"""
Sentinel API entry point.

A thin interface over the existing decision pipeline
(conflict_matrix -> resolve -> weigh -> govern -> executor) and persistence
layer (backend/persistence/, Supabase). This file wires the FastAPI app and
mounts backend.api.router; it contains no route logic and no decision logic
of its own -- see backend/api/ for that.

backend/database/ (SQLite/SQLAlchemy) was retired as dead scaffolding
(docs/data_layer_design.md Q.1) and is not used here.

The demo web UI (frontend/) is served as static files from this same process
so the browser calls /api/* same-origin -- no CORS configuration, no second
dev server, and no Supabase credential ever needs to reach the browser.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api.errors import install_error_handlers
from api.router import router

app = FastAPI(
    title="Sentinel API",
    description=(
        "A thin interface over Sentinel's existing decision pipeline and Supabase "
        "persistence layer. This API sequences already-existing pipeline functions "
        "and never makes a governance decision of its own; GOVERN remains the sole "
        "authorization boundary."
    ),
    version="1.0.0",
)

install_error_handlers(app)
app.include_router(router)

_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.is_dir() and (_FRONTEND_DIR / "index.html").is_file():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIR), html=True), name="frontend")
else:

    @app.get("/", include_in_schema=False)
    def root():
        return {"message": "Sentinel API -- see /docs for the full route list."}
