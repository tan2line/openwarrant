import { describe, it, expect } from "vitest";
import {
  WarrantEngine,
  Decision,
  type Warrant,
  type WarrantRequest,
} from "../src/index.js";

function makeWarrant(overrides: Partial<Warrant> = {}): Warrant {
  return {
    id: "test-warrant-001",
    issuer: "Test Issuer",
    signature: "ed25519:test",
    roles: ["attending_physician", "care_coordinator"],
    actions: ["read-patient-record", "send-patient-data"],
    dataTypes: ["PHI", "clinical-notes"],
    conditions: [
      { patient_consent: "required" },
      { recipient_verified: "required" },
    ],
    validFrom: new Date("2026-01-01T00:00:00Z"),
    validUntil: new Date("2026-12-31T23:59:59Z"),
    trustLevelRequired: 0,
    auditRequired: true,
    escalationTarget: "compliance@test.org",
    notes: "Test warrant",
    ...overrides,
  };
}

describe("WarrantEngine", () => {
  it("returns AUTHORIZED when all conditions are met", () => {
    const engine = new WarrantEngine({ warrants: [makeWarrant()] });

    const request: WarrantRequest = {
      agentId: "agent-001",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: {
        patient_consent: true,
        recipient_verified: true,
      },
      timestamp: new Date("2026-06-15T00:00:00Z"),
    };

    const response = engine.check(request);
    expect(response.decision).toBe(Decision.AUTHORIZED);
    expect(response.warrantId).toBe("test-warrant-001");
    expect(response.authority?.issuer).toBe("Test Issuer");
    expect(response.conditionsEvaluated.every((c) => c.met)).toBe(true);
    expect(response.auditHash).toMatch(/^sha256:/);
  });

  it("returns DENIED when conditions are not met", () => {
    const engine = new WarrantEngine({ warrants: [makeWarrant()] });

    const request: WarrantRequest = {
      agentId: "agent-001",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: {
        patient_consent: false,
        recipient_verified: true,
      },
      timestamp: new Date("2026-06-15T00:00:00Z"),
    };

    const response = engine.check(request);
    expect(response.decision).toBe(Decision.DENIED);
    expect(response.warrantId).toBe("test-warrant-001");
    const failed = response.conditionsEvaluated.filter((c) => !c.met);
    expect(failed.length).toBeGreaterThanOrEqual(1);
    expect(failed.some((c) => c.condition === "patient_consent")).toBe(true);
  });

  it("returns ESCALATE when escalation threshold is exceeded", () => {
    const warrant = makeWarrant({
      conditions: [
        { patient_consent: "required" },
        { single_trade_limit: 50000 },
      ],
    });
    const engine = new WarrantEngine({ warrants: [warrant] });

    const request: WarrantRequest = {
      agentId: "agent-001",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: {
        patient_consent: true,
        amount: 75000,
      },
      timestamp: new Date("2026-06-15T00:00:00Z"),
    };

    const response = engine.check(request);
    expect(response.decision).toBe(Decision.ESCALATE);
    expect(response.warrantId).toBe("test-warrant-001");
  });

  it("returns NO_WARRANT when no matching warrant exists", () => {
    const engine = new WarrantEngine({ warrants: [makeWarrant()] });

    const request: WarrantRequest = {
      agentId: "agent-001",
      action: "delete-everything",
      role: "random_person",
      dataType: "top-secret",
      context: {},
      timestamp: new Date("2026-06-15T00:00:00Z"),
    };

    const response = engine.check(request);
    expect(response.decision).toBe(Decision.NO_WARRANT);
    expect(response.warrantId).toBeUndefined();
  });

  it("returns EXPIRED when warrant is expired", () => {
    const warrant = makeWarrant({
      validFrom: new Date("2024-01-01T00:00:00Z"),
      validUntil: new Date("2024-12-31T23:59:59Z"),
    });
    const engine = new WarrantEngine({ warrants: [warrant] });

    const request: WarrantRequest = {
      agentId: "agent-001",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: {},
      timestamp: new Date("2026-06-15T00:00:00Z"),
    };

    const response = engine.check(request);
    expect(response.decision).toBe(Decision.EXPIRED);
    expect(response.warrantId).toBe("test-warrant-001");
  });

  it("fires event hooks on decisions", () => {
    const authorizedCalls: unknown[] = [];
    const deniedCalls: unknown[] = [];

    const engine = new WarrantEngine({
      warrants: [makeWarrant()],
      onAuthorized: (r) => authorizedCalls.push(r),
      onDenied: (r) => deniedCalls.push(r),
    });

    engine.check({
      agentId: "agent-001",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: { patient_consent: true, recipient_verified: true },
      timestamp: new Date("2026-06-15T00:00:00Z"),
    });
    expect(authorizedCalls.length).toBe(1);

    engine.check({
      agentId: "agent-001",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: { patient_consent: false, recipient_verified: true },
      timestamp: new Date("2026-06-15T00:00:00Z"),
    });
    expect(deniedCalls.length).toBe(1);
  });

  it("stores correlation_id in audit records", () => {
    const engine = new WarrantEngine({ warrants: [makeWarrant()] });

    engine.check({
      agentId: "agent-001",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: { patient_consent: true, recipient_verified: true },
      timestamp: new Date("2026-06-15T00:00:00Z"),
      correlationId: "corr-abc-123",
    });

    const chain = engine.audit.chain;
    expect(chain.length).toBe(1);
    expect(chain[0].correlationId).toBe("corr-abc-123");
  });

  it("builds an audit chain across multiple checks", () => {
    const engine = new WarrantEngine({ warrants: [makeWarrant()] });

    engine.check({
      agentId: "a1",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: { patient_consent: true, recipient_verified: true },
      timestamp: new Date("2026-06-15T00:00:00Z"),
    });

    engine.check({
      agentId: "a2",
      action: "read-patient-record",
      role: "attending_physician",
      dataType: "PHI",
      context: { patient_consent: false, recipient_verified: true },
      timestamp: new Date("2026-06-15T00:00:00Z"),
    });

    const chain = engine.audit.chain;
    expect(chain.length).toBe(2);
    expect(chain[1].previousHash).toBe(chain[0].recordHash);
    expect(engine.audit.verifyChain()).toBe(true);
  });
});
