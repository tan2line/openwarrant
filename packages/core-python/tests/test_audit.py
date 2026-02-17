"""Tests for the audit chain — hash chain integrity."""

from openwarrant import Decision, WarrantResponse, ConditionResult
from openwarrant.audit import AuditChain


def _make_response(decision: Decision = Decision.AUTHORIZED) -> WarrantResponse:
    """Helper to create a test response."""
    return WarrantResponse(
        decision=decision,
        warrant_id="test-warrant-001",
        conditions_evaluated=[
            ConditionResult(condition="test_cond", met=True, detail="ok"),
        ],
    )


def test_empty_chain_is_valid():
    """An empty chain should verify as valid."""
    chain = AuditChain()
    assert chain.verify_chain()
    assert len(chain) == 0


def test_single_record():
    """A chain with one record should be valid."""
    chain = AuditChain()
    response = _make_response()
    record = chain.record(response, agent_id="agent-001", action="test-action")

    assert len(chain) == 1
    assert record.record_hash.startswith("sha256:")
    assert record.previous_hash == AuditChain.GENESIS_HASH
    assert chain.verify_chain()


def test_chain_links():
    """Each record's previous_hash should link to the prior record's hash."""
    chain = AuditChain()

    r1 = chain.record(_make_response(), agent_id="a1", action="act1")
    r2 = chain.record(_make_response(), agent_id="a2", action="act2")
    r3 = chain.record(_make_response(), agent_id="a3", action="act3")

    assert r1.previous_hash == AuditChain.GENESIS_HASH
    assert r2.previous_hash == r1.record_hash
    assert r3.previous_hash == r2.record_hash
    assert chain.verify_chain()


def test_tamper_detection():
    """Modifying a record should break chain verification."""
    chain = AuditChain()

    chain.record(_make_response(), agent_id="a1", action="act1")
    chain.record(_make_response(), agent_id="a2", action="act2")
    chain.record(_make_response(), agent_id="a3", action="act3")

    assert chain.verify_chain()

    # Tamper with the second record's previous_hash
    chain._chain[1].previous_hash = "sha256:tampered"
    assert not chain.verify_chain()


def test_last_hash_updates():
    """last_hash should always reflect the most recent record."""
    chain = AuditChain()
    assert chain.last_hash == AuditChain.GENESIS_HASH

    r1 = chain.record(_make_response(), agent_id="a1", action="act1")
    assert chain.last_hash == r1.record_hash

    r2 = chain.record(_make_response(), agent_id="a2", action="act2")
    assert chain.last_hash == r2.record_hash


def test_on_record_callback():
    """The on_record callback should fire for each record."""
    records = []
    chain = AuditChain(on_record=lambda r: records.append(r))

    chain.record(_make_response(), agent_id="a1", action="act1")
    chain.record(_make_response(), agent_id="a2", action="act2")

    assert len(records) == 2
    assert records[0].agent_id == "a1"
    assert records[1].agent_id == "a2"


def test_correlation_id_in_audit():
    """Correlation ID should be stored in audit records."""
    chain = AuditChain()
    record = chain.record(
        _make_response(),
        agent_id="a1",
        action="act1",
        correlation_id="corr-xyz",
    )
    assert record.correlation_id == "corr-xyz"


def test_different_decisions_recorded():
    """Different decision types should all be recorded correctly."""
    chain = AuditChain()

    for decision in Decision:
        chain.record(
            _make_response(decision),
            agent_id="agent",
            action="action",
        )

    assert len(chain) == 5
    decisions = [r.decision for r in chain.chain]
    assert "AUTHORIZED" in decisions
    assert "DENIED" in decisions
    assert "ESCALATE" in decisions
    assert "NO_WARRANT" in decisions
    assert "EXPIRED" in decisions
    assert chain.verify_chain()
