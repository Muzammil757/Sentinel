"""
EXECUTOR constants: versions, the closed status and code vocabularies, and
the GOVERN fields EXECUTOR requires before it will act.

Constants only -- no logic, mirroring weigh/schema.py and govern/schema.py.

Nothing here is policy. Policy lives in the bundle GOVERN enforced; by the
time EXECUTOR runs, every policy question has already been answered upstream
and EXECUTOR's only remaining job is to check that the answer it was handed
really is GOVERN's, and then do exactly what it says.
"""

EXECUTOR_VERSION = "1.0.0"
EXECUTION_METHOD = "mock_execution_v1"

# Every effect this layer produces is simulated in-process. Stated as data on
# the receipt so a reader never has to infer it.
EXECUTION_MODE = "mock"

# EXECUTOR has exactly one source of authority, named on every receipt.
AUTHORIZATION_SOURCE = "GOVERN"

# The one GOVERN outcome that authorizes anything. Must equal
# govern.schema.OUTCOME_PROCEED; duplicated rather than imported because
# EXECUTOR's source imports no deciding layer at all (test_executor_safety.py
# asserts both halves of that: the absent import, and this equality).
AUTHORIZING_OUTCOME = "PROCEED"

# --- receipt statuses ------------------------------------------------------

STATUS_EXECUTED = "EXECUTED"
STATUS_REJECTED = "REJECTED"

# --- the authorization ladder ---------------------------------------------

CHECK_PASS = "PASS"
CHECK_FAIL = "FAIL"

CHECK_GOVERN_OUTPUT_WELL_FORMED = "GOVERN_OUTPUT_WELL_FORMED"
CHECK_EXECUTION_AUTHORIZED_BY_GOVERN = "EXECUTION_AUTHORIZED_BY_GOVERN"
CHECK_OUTCOME_CONSISTENT_WITH_AUTHORIZATION = "OUTCOME_CONSISTENT_WITH_AUTHORIZATION"
CHECK_AUTHORIZED_CANDIDATE_PRESENT = "AUTHORIZED_CANDIDATE_PRESENT"
CHECK_AUTHORIZED_CANDIDATE_PERMITTED = "AUTHORIZED_CANDIDATE_PERMITTED"
CHECK_AUTHORIZED_ACTIONS_MATCH_CANDIDATE = "AUTHORIZED_ACTIONS_MATCH_CANDIDATE"
CHECK_AUTHORIZED_ACTION_PRESENT = "AUTHORIZED_ACTION_PRESENT"
CHECK_REQUEST_MATCHES_AUTHORIZATION = "REQUEST_MATCHES_AUTHORIZATION"
CHECK_ACTIONS_SUPPORTED = "ACTIONS_SUPPORTED"

# The fixed order the ladder runs in. The receipt lists the checks that ran,
# in this order, stopping at the first failure -- so "how far did EXECUTOR
# get, and where did it stop?" is answerable from the receipt alone.
CHECK_ORDER = (
    CHECK_GOVERN_OUTPUT_WELL_FORMED,
    CHECK_EXECUTION_AUTHORIZED_BY_GOVERN,
    CHECK_OUTCOME_CONSISTENT_WITH_AUTHORIZATION,
    CHECK_AUTHORIZED_CANDIDATE_PRESENT,
    CHECK_AUTHORIZED_CANDIDATE_PERMITTED,
    CHECK_AUTHORIZED_ACTIONS_MATCH_CANDIDATE,
    CHECK_AUTHORIZED_ACTION_PRESENT,
    CHECK_REQUEST_MATCHES_AUTHORIZATION,
    CHECK_ACTIONS_SUPPORTED,
)

# --- rejection codes -------------------------------------------------------

REJECT_AUTHORIZATION_MISSING = "AUTHORIZATION_MISSING"
REJECT_GOVERN_OUTPUT_MALFORMED = "GOVERN_OUTPUT_MALFORMED"
REJECT_EXECUTION_NOT_AUTHORIZED = "EXECUTION_NOT_AUTHORIZED"
REJECT_AUTHORIZATION_INCONSISTENT = "AUTHORIZATION_INCONSISTENT"
REJECT_AUTHORIZED_CANDIDATE_MISSING = "AUTHORIZED_CANDIDATE_MISSING"
REJECT_CANDIDATE_NOT_PERMITTED = "CANDIDATE_NOT_PERMITTED"
REJECT_AUTHORIZED_ACTION_MISSING = "AUTHORIZED_ACTION_MISSING"
REJECT_REQUEST_MALFORMED = "REQUEST_MALFORMED"
REJECT_REQUESTED_CANDIDATE_MISMATCH = "REQUESTED_CANDIDATE_MISMATCH"
REJECT_REQUESTED_ACTION_MISMATCH = "REQUESTED_ACTION_MISMATCH"
REJECT_UNSUPPORTED_ACTION = "UNSUPPORTED_ACTION"

REJECTION_CODES = frozenset(
    {
        REJECT_AUTHORIZATION_MISSING,
        REJECT_GOVERN_OUTPUT_MALFORMED,
        REJECT_EXECUTION_NOT_AUTHORIZED,
        REJECT_AUTHORIZATION_INCONSISTENT,
        REJECT_AUTHORIZED_CANDIDATE_MISSING,
        REJECT_CANDIDATE_NOT_PERMITTED,
        REJECT_AUTHORIZED_ACTION_MISSING,
        REJECT_REQUEST_MALFORMED,
        REJECT_REQUESTED_CANDIDATE_MISMATCH,
        REJECT_REQUESTED_ACTION_MISMATCH,
        REJECT_UNSUPPORTED_ACTION,
    }
)

# --- the govern_output contract EXECUTOR reads ----------------------------

# Only what EXECUTOR actually needs. It deliberately does NOT require the
# comparative machinery (score_band, weights_used, objectives_considered):
# EXECUTOR neither reads nor re-derives any of it.
REQUIRED_GOVERN_KEYS = frozenset(
    {
        "govern_version",
        "decision_id",
        "policy_id",
        "policy_version",
        "policy_hash",
        "case",
        "outcome",
        "outcome_basis",
        "execution_authorized",
        "selected_candidate",
        "authorized_actions",
        "permission_evaluation",
        "rationale",
    }
)

REQUIRED_SELECTED_CANDIDATE_KEYS = frozenset(
    {"candidate_id", "strategy", "resulting_actions", "permission_basis"}
)

REQUIRED_PERMISSION_EVALUATION_KEYS = frozenset({"candidates", "permitted_candidate_ids"})

REQUIRED_PERMISSION_RECORD_KEYS = frozenset(
    {"candidate_id", "resulting_actions", "permitted", "blocking_reasons"}
)

# --- the execution request -------------------------------------------------

# An optional caller assertion of what it believes it is executing. EXECUTOR
# never reads it to decide anything -- it only compares it against GOVERN's
# authorization and refuses on any difference.
REQUEST_FIELDS = frozenset({"candidate_id", "actions"})

RECEIPT_ID_PREFIX = "exe_"
