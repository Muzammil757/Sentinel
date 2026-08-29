"""
Typed API errors and the exception handlers that turn them into consistent,
safe HTTP responses.

Every handler here returns a small JSON envelope -- `{"error": {"code",
"message"}}` -- and never a raw stack trace, a Supabase URL, a service-role
key, or any other internal/environment value. Distinct error *codes* let a
client (or a test) tell a case-not-found apart from a run-not-found apart
from a persistence failure apart from a pipeline failure, per the API
contract's error-handling section.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from persistence.connection import SupabaseConfigError
from persistence.errors import PersistenceError


class ApiError(Exception):
    """Base class for every error this API layer raises deliberately."""

    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class CaseNotFoundError(ApiError):
    status_code = 404
    code = "case_not_found"


class RunNotFoundError(ApiError):
    status_code = 404
    code = "run_not_found"


class ScenarioNotFoundError(ApiError):
    status_code = 404
    code = "scenario_not_found"


class UnsupportedOperationError(ApiError):
    """A request that names a real but currently-unsupported capability
    (e.g. review action "override") -- refused explicitly rather than
    silently accepted or invented on the spot."""

    status_code = 400
    code = "unsupported_operation"


class PipelineFailureError(ApiError):
    """
    A pipeline stage (WEIGH/GOVERN/EXECUTOR/conflict/resolve) raised while
    processing a request whose evidence could not even be scored -- this is
    distinct from a *pipeline outcome* like ESCALATE or a REJECTED receipt,
    both of which are successful, fully-audited runs and are returned as
    normal 200 responses. This error exists only for the rarer case where
    the API cannot even construct a run record (e.g. the case row itself
    could not be created).
    """

    status_code = 422
    code = "pipeline_failure"


def _error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_error_body(exc.code, exc.message))

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Request failed validation."),
        )

    @app.exception_handler(SupabaseConfigError)
    async def _handle_supabase_config_error(request: Request, exc: SupabaseConfigError) -> JSONResponse:
        # Never echo the exception text verbatim -- persistence.connection's
        # own message is safe (names only env var names, no values), but the
        # handler is written defensively so a future message change cannot
        # leak a credential through this path.
        return JSONResponse(
            status_code=503,
            content=_error_body(
                "persistence_unavailable",
                "The persistence layer is not configured or unreachable.",
            ),
        )

    @app.exception_handler(PersistenceError)
    async def _handle_persistence_error(request: Request, exc: PersistenceError) -> JSONResponse:
        return JSONResponse(
            status_code=502,
            content=_error_body("persistence_failure", "The persistence layer rejected this write."),
        )

    # postgrest.exceptions.APIError is what the real `supabase` client raises
    # from `.execute()` on any REST-level failure (a missing table, a bad
    # filter, a connectivity problem) -- imported lazily and defensively,
    # mirroring persistence.connection's own lazy import of `supabase`, so
    # this module still loads in an environment without the package
    # installed. Handled distinctly from ApiError/PersistenceError so a
    # client can still tell "the database rejected this" apart from "this
    # API layer raised something deliberately."
    try:
        from postgrest.exceptions import APIError as _PostgrestAPIError

        @app.exception_handler(_PostgrestAPIError)
        async def _handle_postgrest_error(request: Request, exc: _PostgrestAPIError) -> JSONResponse:
            return JSONResponse(
                status_code=502,
                content=_error_body(
                    "persistence_failure", "The persistence layer rejected this request."
                ),
            )
    except ImportError:
        pass

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_error_body("internal_error", "An unexpected error occurred."),
        )
