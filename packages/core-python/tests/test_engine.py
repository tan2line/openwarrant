"""Tests for the WarrantEngine — all 5 decision types."""

from datetime import datetime, timedelta

from openwarrant import (
    Decision,
    Warrant,
    WarrantEngine,
    WarrantRequest,
)


def _make_warrant(**overrides) -> Warrant:
    """Helper to create a test warrant with sensible defaults."""
    defaults = dict(
        id="test-warrant-001",
        issuer="Test Issuer",
        signature="ed25519:test",
        roles=["attending_physician", "care_coordinator"],
        actions=["read-patient-record", "send-patient-data"],
        data_types=["PHI", "clinical-notes"],
        conditions=[
            {"patient_consent": "required"},
            {"recipient_verified": "required"},
        ],
        valid_from=datetime(2026, 1, 1),
        valid_until=datetime(2026, 12, 31, 23, 59, 59),
        trust_level_required=0,
        audit_required=True,
        escalation_target="compliance@test.org",
        notes="Test warrant",
    )
    defaults.update(overrides)
    return Warrant(**defaults)


def test_authorized():
    """AUTHORIZED: valid warrant, all conditions met."""
    warrant = _make_warrant()
    engine = WarrantEngine(warrants=[warrant])

    request = WarrantRequest(
        agent_id="agent-001",
        action="read-patient-record",
        role="attending_physician",
        data_type="PHI",
        context={
            "patient_consent": True,
            "recipient_verified": True,
        },
        timestamp=datetime(2026, 6, 15),
    )

    response = engine.check(request)
    assert response.decision == Decision.AUTHORIZED
    assert response.warrant_id == "test-warrant-001"
    assert response.authority is not None
    assert response.authority.issuer == "Test Issuer"
    assert all(c.met for c in response.conditions_evaluated)
    assert response.audit_hash.startswith("sha256:")


def test_denied():
    """DENIED: valid warrant but conditions not met."""
    warrant = _make_warrant()
    engine = WarrantEngine(warrants=[warrant])

    request = WarrantRequest(
        agent_id="agent-001",
        action="read-patient-record",
        role="attending_physician",
        data_type="PHI",
        context={
            "patient_consent": False,
            "recipient_verified": True,
        },
        timestamp=datetime(2026, 6, 15),
    )

    response = engine.check(request)
    assert response.decision == Decision.DENIED
    assert response.warrant_id == "test-warrant-001"
    failed = [c for c in response.conditions_evaluated if not c.met]
    assert len(failed) >= 1
    assert any("patient_consent" in c.condition for c in failed)


def test_escalate():
    """ESCALATE: warrant matches but escalation threshold exceeded."""
    warrant = _make_warrant(
        conditions=[
            {"patient_consent": "required"},
            {"single_trade_limit": 50000},
        ]
    )
    engine = WarrantEngine(warrants=[warrant])

    request = WarrantRequest(
        agent_id="agent-001",
        action="read-patient-record",
        role="attending_physician",
        data_type="PHI",
        context={
            "patient_consent": True,
            "amount": 75000,
        },
        timestamp=datetime(2026, 6, 15),
    )

    response = engine.check(request)
    assert response.decision == Decision.ESCALATE
    assert response.warrant_id == "test-warrant-001"


def test_no_warrant():
    """NO_WARRANT: no matching warrant found."""
    warrant = _make_warrant()
    engine = WarrantEngine(warrants=[warrant])

    request = WarrantRequest(
        agent_id="agent-001",
        action="delete-everything",
        role="random_person",
        data_type="top-secret",
        timestamp=datetime(2026, 6, 15),
    )

    response = engine.check(request)
    assert response.decision == Decision.NO_WARRANT
    assert response.warrant_id is None


def test_expired():
    """EXPIRED: warrant found but expired."""
    warrant = _make_warrant(
        valid_from=datetime(2024, 1, 1),
        valid_until=datetime(2024, 12, 31),
    )
    engine = WarrantEngine(warrants=[warrant])

    request = WarrantRequest(
        agent_id="agent-001",
        action="read-patient-record",
        role="attending_physician",
        data_type="PHI",
        timestamp=datetime(2026, 6, 15),
    )

    response = engine.check(request)
    assert response.decision == Decision.EXPIRED
    assert response.warrant_id == "test-warrant-001"


def test_loads_warrants_from_directory(tmp_path):
    """Engine can load warrants from a directory of YAML files."""
    warrant_file = tmp_path / "test.yaml"
    warrant_file.write_text(
        """warrant:
  id: "file-test-001"
  issuer: "File Test"
  signature: "ed25519:test"
  who_can_act:
    roles:
      - "tester"
  what_they_can_do:
    actions:
      - "test-action"
    data_types:
      - "test-data"
  under_what_conditions:
    - test_cond: required
  valid_from: "2026-01-01T00:00:00Z"
  valid_until: "2026-12-31T23:59:59Z"
  audit_required: true
"""
    )

    engine = WarrantEngine(warrant_store=tmp_path)
    assert len(engine.warrants) == 1
    assert engine.warrants[0].id == "file-test-001"


def test_event_hooks():
    """Event hooks fire on decisions."""
    authorized_calls = []
    denied_calls = []

    warrant = _make_warrant()
    engine = WarrantEngine(
        warrants=[warrant],
        on_authorized=lambda r: authorized_calls.append(r),
        on_denied=lambda r: denied_calls.append(r),
    )

    # Authorized
    engine.check(
        WarrantRequest(
            agent_id="agent-001",
            action="read-patient-record",
            role="attending_physician",
            data_type="PHI",
            context={"patient_consent": True, "recipient_verified": True},
            timestamp=datetime(2026, 6, 15),
        )
    )
    assert len(authorized_calls) == 1

    # Denied
    engine.check(
        WarrantRequest(
            agent_id="agent-001",
            action="read-patient-record",
            role="attending_physician",
            data_type="PHI",
            context={"patient_consent": False, "recipient_verified": True},
            timestamp=datetime(2026, 6, 15),
        )
    )
    assert len(denied_calls) == 1


def test_correlation_id():
    """Correlation ID flows through to audit records."""
    warrant = _make_warrant()
    engine = WarrantEngine(warrants=[warrant])

    request = WarrantRequest(
        agent_id="agent-001",
        action="read-patient-record",
        role="attending_physician",
        data_type="PHI",
        context={"patient_consent": True, "recipient_verified": True},
        timestamp=datetime(2026, 6, 15),
        correlation_id="corr-abc-123",
    )

    engine.check(request)
    chain = engine.audit.chain
    assert len(chain) == 1
    assert chain[0].correlation_id == "corr-abc-123"
