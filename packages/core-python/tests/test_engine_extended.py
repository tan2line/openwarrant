"""Extended engine tests — structured constraints, wildcards, status, capabilities, multi-warrant."""

from datetime import datetime

from openwarrant import (
    Constraint,
    Decision,
    Warrant,
    WarrantEngine,
    WarrantRequest,
    WarrantStatus,
)


def _make_warrant(**overrides) -> Warrant:
    defaults = dict(
        id="test-warrant-001",
        issuer="Test Issuer",
        signature="ed25519:test",
        roles=["attending_physician", "care_coordinator"],
        actions=["read-patient-record", "send-patient-data"],
        data_types=["PHI", "clinical-notes"],
        conditions=[],
        valid_from=datetime(2026, 1, 1),
        valid_until=datetime(2026, 12, 31, 23, 59, 59),
    )
    defaults.update(overrides)
    return Warrant(**defaults)


# --- Wildcard action matching ---

def test_wildcard_action_match():
    w = _make_warrant(actions=["read-patient-record", "cds.alert.*"])
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="cds.alert.sepsis",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


def test_wildcard_action_no_match():
    w = _make_warrant(actions=["cds.alert.*"])
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="doc.generate",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.NO_WARRANT


# --- Optional role / data_type ---

def test_empty_role_matches_any_warrant():
    w = _make_warrant()
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


def test_empty_data_type_matches_any_warrant():
    w = _make_warrant()
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


def test_warrant_with_empty_roles_matches_any_role():
    w = _make_warrant(roles=[])
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="any_role", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


# --- Warrant status ---

def test_revoked_warrant_skipped():
    w = _make_warrant(status=WarrantStatus.REVOKED)
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.DENIED
    assert any("revoked" in r for r in resp.deny_reasons)


def test_suspended_warrant_skipped():
    w = _make_warrant(status=WarrantStatus.SUSPENDED)
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.DENIED
    assert any("suspended" in r for r in resp.deny_reasons)


def test_active_warrant_allowed():
    w = _make_warrant(status=WarrantStatus.ACTIVE)
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


def test_none_status_treated_as_active():
    w = _make_warrant(status=None)
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


# --- Structured constraints ---

def test_structured_constraints_pass():
    w = _make_warrant(
        context_constraints=[
            Constraint(field="setting", operator="eq", value="icu"),
            Constraint(field="age", operator="gte", value=18),
        ],
    )
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        context={"setting": "icu", "age": 62},
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


def test_structured_constraints_fail():
    w = _make_warrant(
        context_constraints=[
            Constraint(field="setting", operator="eq", value="ed"),
        ],
    )
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        context={"setting": "icu"},
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision != Decision.AUTHORIZED


# --- Capability allowlist ---

def test_capability_allowed():
    w = _make_warrant(
        allowed_capabilities=[{"name": "sepsis_model", "version": "3.2"}],
    )
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        context={"__capability": {"name": "sepsis_model", "version": "3.2"}},
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


def test_capability_not_allowed():
    w = _make_warrant(
        allowed_capabilities=[{"name": "other_model", "version": "1.0"}],
    )
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        context={"__capability": {"name": "sepsis_model", "version": "3.2"}},
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision != Decision.AUTHORIZED
    assert any("capability_not_allowed" in r for r in resp.deny_reasons)


def test_empty_capability_allowlist_allows_any():
    w = _make_warrant(allowed_capabilities=[])
    engine = WarrantEngine(warrants=[w])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        context={"__capability": {"name": "anything", "version": "0.0"}},
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED


# --- Multi-warrant iteration ---

def test_multi_warrant_first_matching_wins():
    w1 = _make_warrant(id="w1", actions=["doc.generate"])
    w2 = _make_warrant(id="w2", actions=["read-patient-record"])
    engine = WarrantEngine(warrants=[w1, w2])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED
    assert resp.warrant_id == "w2"


def test_multi_warrant_skips_revoked():
    w1 = _make_warrant(id="w1", status=WarrantStatus.REVOKED)
    w2 = _make_warrant(id="w2", status=WarrantStatus.ACTIVE)
    engine = WarrantEngine(warrants=[w1, w2])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.AUTHORIZED
    assert resp.warrant_id == "w2"


def test_deny_reasons_collected():
    w1 = _make_warrant(id="w1", status=WarrantStatus.REVOKED)
    w2 = _make_warrant(id="w2", status=WarrantStatus.SUSPENDED)
    engine = WarrantEngine(warrants=[w1, w2])
    resp = engine.check(WarrantRequest(
        agent_id="a", action="read-patient-record",
        role="attending_physician", data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    ))
    assert resp.decision == Decision.DENIED
    assert len(resp.deny_reasons) == 2
