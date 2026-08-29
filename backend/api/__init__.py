"""
Sentinel API layer.

A thin interface over the existing decision pipeline
(conflict_matrix -> resolve -> weigh -> govern -> executor) and the existing
Supabase persistence layer (backend/persistence/). This package contains no
decision logic of its own: it sequences already-existing pure functions,
shapes their output into HTTP responses, and writes through
persistence.store.PersistenceStore / reads through persistence.reader.CaseReader.

    backend.api.schemas      -- request/response models (Pydantic)
    backend.api.errors       -- typed API errors -> consistent HTTP responses
    backend.api.orchestrator -- runs the real pipeline once, persists every stage
    backend.api.scenarios    -- curated Scenario Lab fixtures, run through the real pipeline
    backend.api.service      -- read-model assembly (case list/detail/decision/evidence/timeline)
    backend.api.router       -- FastAPI route handlers (thin; delegate to the above)
"""
