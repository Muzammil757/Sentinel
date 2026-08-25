"""
PERSISTENCE: the passive sink downstream of EXECUTOR
(docs/data_layer_design.md).

Persistence stores what the decision pipeline already produced. It does not
score, rank, authorize, execute, or reinterpret anything -- every dict handed
to this package has already been fully decided by RESOLVE, WEIGH, GOVERN, or
EXECUTOR. This package's only questions are: where does this go, how do I
find it again, and can I prove nothing was altered after the fact.

Public surface:

    persistence.store.PersistenceStore   -- one method per pipeline stage
    persistence.mappers                  -- pure stage-output -> row mapping
    persistence.connection.get_client    -- lazy Supabase client factory
    persistence.audit                    -- audit_events stage/outcome vocabulary
    persistence.errors.PersistenceError  -- integrity failures (never decisions)
"""

from persistence.errors import PersistenceError
from persistence.store import PersistenceStore

__all__ = ["PersistenceStore", "PersistenceError"]
