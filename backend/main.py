"""
Placeholder entry point only -- not the real API.

backend/database/ (SQLite/SQLAlchemy) was retired as dead scaffolding
(docs/data_layer_design.md Q.1): nothing in the decision pipeline or
backend/persistence/ ever read from or wrote to it. This file no longer
imports it. The real persistence layer is backend/persistence/ (Supabase);
future API routes should be built against that, not a reintroduced SQLite
layer.
"""

from fastapi import FastAPI

app = FastAPI(title="Sentinel API")


@app.get("/")
def root():
    return {
        "message": "Sentinel API placeholder -- no routes implemented yet",
    }
