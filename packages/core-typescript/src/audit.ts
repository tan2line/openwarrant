/** SHA-256 hash-chained audit trail for OpenWarrant. */

import { createHash } from "crypto";
import type { WarrantResponse, ConditionResult } from "./models.js";

export interface AuditRecord {
  recordId: string;
  timestamp: string;
  agentId: string;
  warrantId?: string;
  action: string;
  decision: string;
  conditionsEvaluated: { condition: string; met: boolean; detail: string }[];
  correlationId?: string;
  previousHash: string;
  recordHash: string;
}

export class AuditChain {
  static readonly GENESIS_HASH = "sha256:" + "0".repeat(64);

  private _chain: AuditRecord[] = [];
  private _previousHash: string = AuditChain.GENESIS_HASH;
  private _onRecord?: (record: AuditRecord) => void;

  constructor(options?: { onRecord?: (record: AuditRecord) => void }) {
    this._onRecord = options?.onRecord;
  }

  get chain(): AuditRecord[] {
    return [...this._chain];
  }

  get lastHash(): string {
    return this._previousHash;
  }

  get length(): number {
    return this._chain.length;
  }

  private computeHash(content: string, previousHash: string): string {
    const raw = content + previousHash;
    const digest = createHash("sha256").update(raw, "utf-8").digest("hex");
    return `sha256:${digest}`;
  }

  record(
    response: WarrantResponse,
    agentId: string,
    action: string,
    correlationId?: string
  ): AuditRecord {
    const conditions = response.conditionsEvaluated.map((c) => ({
      condition: c.condition,
      met: c.met,
      detail: c.detail,
    }));

    const content = JSON.stringify(
      {
        agent_id: agentId,
        warrant_id: response.warrantId ?? null,
        action,
        decision: response.decision,
        conditions,
        correlation_id: correlationId ?? null,
        timestamp: new Date().toISOString(),
      },
      Object.keys({
        action: 1,
        agent_id: 1,
        conditions: 1,
        correlation_id: 1,
        decision: 1,
        timestamp: 1,
        warrant_id: 1,
      }).sort()
    );

    const recordHash = this.computeHash(content, this._previousHash);

    const record: AuditRecord = {
      recordId: `aud-${Math.random().toString(36).substring(2, 14)}`,
      timestamp: new Date().toISOString(),
      agentId,
      warrantId: response.warrantId,
      action,
      decision: response.decision,
      conditionsEvaluated: conditions,
      correlationId,
      previousHash: this._previousHash,
      recordHash,
    };

    this._chain.push(record);
    this._previousHash = recordHash;

    if (this._onRecord) {
      this._onRecord(record);
    }

    return record;
  }

  verifyChain(): boolean {
    if (this._chain.length === 0) return true;

    let expectedPrev = AuditChain.GENESIS_HASH;
    for (const record of this._chain) {
      if (record.previousHash !== expectedPrev) return false;
      expectedPrev = record.recordHash;
    }

    return true;
  }
}
