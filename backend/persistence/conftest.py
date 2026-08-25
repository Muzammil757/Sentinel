"""
Shared persistence test fixtures.

Two kinds of fixture, mirroring the project's existing testing stance
(govern/conftest.py, executor/conftest.py): stage documents come from running
the REAL pipeline, never a hand-written stand-in that can drift from what the
decision layers actually emit, and the database is a tiny in-memory fake --
there is no live Supabase/Postgres project available in this environment
(see the final report's "local testing strategy" section).
"""

import copy
import uuid

from conflict_matrix.integration import evaluate_agent_actions
from executor import execute
from govern import decide
from govern.conftest import build_case, no_conflict_release_case, rto_vs_retention_case
from resolve.resolver import generate_resolution_candidates

# --- the fake Supabase client -----------------------------------------------


class _Response:
    def __init__(self, data):
        self.data = data


class _SelectQuery:
    def __init__(self, rows):
        self._rows = rows
        self._filters = []

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def execute(self):
        rows = self._rows
        for column, value in self._filters:
            rows = [row for row in rows if row.get(column) == value]
        return _Response(copy.deepcopy(rows))


class _UpdateQuery:
    def __init__(self, rows, values):
        self._rows = rows
        self._values = values
        self._filters = []

    def eq(self, column, value):
        self._filters.append((column, value))
        return self

    def execute(self):
        matched = []
        for row in self._rows:
            if all(row.get(column) == value for column, value in self._filters):
                row.update(self._values)
                matched.append(copy.deepcopy(row))
        return _Response(matched)


class _InsertResult:
    """`.insert(...)` performs the write eagerly (the fake has no network
    round trip to defer); `.execute()` just hands back what was written, to
    match the real client's `insert(...).execute()` call shape."""

    def __init__(self, data):
        self._data = data

    def execute(self):
        return _Response(self._data)


class _Table:
    def __init__(self, all_tables, name):
        self._all_tables = all_tables
        self._name = name

    def select(self, *_columns):
        return _SelectQuery(self._all_tables[self._name])

    def insert(self, rows):
        payload = [rows] if isinstance(rows, dict) else rows
        inserted = []
        for row in payload:
            record = copy.deepcopy(row)
            record.setdefault("id", str(uuid.uuid4()))
            self._all_tables[self._name].append(record)
            inserted.append(copy.deepcopy(record))
        return _InsertResult(inserted)

    def update(self, values):
        return _UpdateQuery(self._all_tables[self._name], values)


class FakeSupabaseClient:
    """
    Minimal in-memory stand-in for the real `supabase` client: just enough of
    `table().insert().execute()`, `table().select().eq().execute()`, and
    `table().update().eq().execute()` to exercise persistence's mapping and
    linkage logic. Never used outside tests -- production code obtains a real
    client from persistence.connection.get_client().
    """

    def __init__(self):
        self._tables = {}

    def table(self, name):
        self._tables.setdefault(name, [])
        return _Table(self._tables, name)

    def rows(self, name):
        return copy.deepcopy(self._tables.get(name, []))


# --- real pipeline fixtures --------------------------------------------------


def full_run_payout_vs_dispute(case_id="case-Q"):
    """
    Every real stage output for one PROCEED case, ready for persistence
    tests: conflict_result, resolve_output, weigh_output, agent_actions,
    case_context, policy, govern_output, receipt. Mirrors
    govern/conftest.py::payout_vs_dispute_case (design section N's worked
    example) but additionally exposes the pre-WEIGH stage documents
    persistence needs that GOVERN's fixtures don't return.
    """

    payouts = {
        "agent": "payouts",
        "proposed_action": "RELEASE_PAYMENT",
        "confidence": 0.95,
        "amount": 42000,
        "days_overdue": 9,
    }
    dispute = {
        "agent": "dispute",
        "proposed_action": "HOLD_RELATED_ACTIONS",
        "confidence": 0.95,
        "dispute_status": "OPEN",
        "disputed_amount": 42000,
    }
    case_context = {"case_id": case_id, "merchant_id": "mrch_001"}

    conflict_result = evaluate_agent_actions(payouts, dispute, "order_vendor")
    resolve_output = generate_resolution_candidates(conflict_result, payouts, dispute)

    weigh_output, agent_actions, case_context, policy = build_case(
        payouts, dispute, "order_vendor", case_context
    )
    govern_output = decide(weigh_output, agent_actions, case_context, policy)
    receipt = execute(govern_output)

    return {
        "conflict_result": conflict_result,
        "resolve_output": resolve_output,
        "weigh_output": weigh_output,
        "agent_actions": agent_actions,
        "case_context": case_context,
        "policy": policy,
        "govern_output": govern_output,
        "receipt": receipt,
    }


def full_run_escalated_release(amount=60000):
    """
    A run whose GOVERN outcome is ESCALATE (over the authority cap) and whose
    EXECUTOR receipt is therefore REJECTED -- design section S.3's
    over-the-cap variant, used to test that persistence records a rejection
    as a rejection.
    """

    payouts = {
        "agent": "payouts",
        "proposed_action": "RELEASE_PAYMENT",
        "confidence": 0.95,
        "amount": amount,
        "days_overdue": 9,
    }
    dispute = {
        "agent": "dispute",
        "proposed_action": "CLOSE_CASE",
        "confidence": 0.90,
        "dispute_status": "CLOSED",
        "disputed_amount": 0,
    }

    conflict_result = evaluate_agent_actions(payouts, dispute, "order_vendor")
    resolve_output = generate_resolution_candidates(conflict_result, payouts, dispute)

    weigh_output, agent_actions, case_context, policy = no_conflict_release_case(amount)
    govern_output = decide(weigh_output, agent_actions, case_context, policy)
    receipt = execute(govern_output)

    return {
        "conflict_result": conflict_result,
        "resolve_output": resolve_output,
        "weigh_output": weigh_output,
        "agent_actions": agent_actions,
        "case_context": case_context,
        "policy": policy,
        "govern_output": govern_output,
        "receipt": receipt,
    }


def full_run_ambiguous():
    """
    A run whose GOVERN outcome is AMBIGUOUS -- design section S.2's near-tie
    between two permitted candidates. `candidate_under_review` is set (unlike
    the escalated-release fixture, where the permitted set is empty) while
    `selected_candidate` stays null and execution_authorized stays false --
    exactly the shape that exercises the difference between the two fields.
    """

    rto = {
        "agent": "rto",
        "proposed_action": "HOLD_ORDER",
        "confidence": 0.95,
        "rto_score": 0.82,
        "shipment_status": "IN_TRANSIT",
    }
    retention = {
        "agent": "retention",
        "proposed_action": "WIN_BACK_OFFER",
        "confidence": 0.95,
        "churn_risk": 0.80,
        "customer_value_score": 0.9,
    }

    conflict_result = evaluate_agent_actions(rto, retention, "customer")
    resolve_output = generate_resolution_candidates(conflict_result, rto, retention)

    weigh_output, agent_actions, case_context, policy = rto_vs_retention_case()
    govern_output = decide(weigh_output, agent_actions, case_context, policy)
    receipt = execute(govern_output)

    return {
        "conflict_result": conflict_result,
        "resolve_output": resolve_output,
        "weigh_output": weigh_output,
        "agent_actions": agent_actions,
        "case_context": case_context,
        "policy": policy,
        "govern_output": govern_output,
        "receipt": receipt,
    }
