/** WarrantEngine — the core authorization engine for OpenWarrant. */

import type {
  Warrant,
  WarrantRequest,
  WarrantResponse,
  ConditionResult,
  WarrantAuthority,
  TrustElevation,
} from "./models.js";
import { Decision } from "./models.js";
import { AuditChain } from "./audit.js";
import { loadWarrantDir, loadWarrantFile } from "./loader.js";
import * as fs from "fs";

export interface WarrantEngineOptions {
  warrantStore?: string;
  warrants?: Warrant[];
  onAuthorized?: (response: WarrantResponse) => void;
  onDenied?: (response: WarrantResponse) => void;
  onEscalate?: (response: WarrantResponse) => void;
  webhookUrl?: string;
  onDecision?: (response: WarrantResponse) => void;
}

export class WarrantEngine {
  private _warrants: Warrant[] = [];
  private _audit = new AuditChain();
  private _onAuthorized?: (response: WarrantResponse) => void;
  private _onDenied?: (response: WarrantResponse) => void;
  private _onEscalate?: (response: WarrantResponse) => void;
  private _webhookUrl?: string;
  private _onDecision?: (response: WarrantResponse) => void;
  private _executionCount = 0;

  constructor(options: WarrantEngineOptions = {}) {
    this._onAuthorized = options.onAuthorized;
    this._onDenied = options.onDenied;
    this._onEscalate = options.onEscalate;
    this._webhookUrl = options.webhookUrl;
    this._onDecision = options.onDecision;

    if (options.warrants) {
      this._warrants = [...options.warrants];
    } else if (options.warrantStore) {
      const stat = fs.statSync(options.warrantStore, { throwIfNoEntry: false });
      if (stat?.isDirectory()) {
        this._warrants = loadWarrantDir(options.warrantStore);
      } else if (stat?.isFile()) {
        this._warrants = [loadWarrantFile(options.warrantStore)];
      }
    }
  }

  get warrants(): Warrant[] {
    return [...this._warrants];
  }

  get audit(): AuditChain {
    return this._audit;
  }

  private findMatchingWarrant(
    action: string,
    role: string,
    dataType: string
  ): Warrant | null {
    for (const w of this._warrants) {
      if (
        w.actions.includes(action) &&
        w.roles.includes(role) &&
        w.dataTypes.includes(dataType)
      ) {
        return w;
      }
    }
    return null;
  }

  private evaluateConditions(
    warrant: Warrant,
    request: WarrantRequest
  ): ConditionResult[] {
    const results: ConditionResult[] = [];
    const ctx = request.context;

    for (const cond of warrant.conditions) {
      for (const [key, value] of Object.entries(cond)) {
        if (key === "escalation_threshold" || key === "single_trade_limit") {
          const amount = (ctx.amount ?? ctx.trade_amount ?? 0) as number;
          const threshold =
            typeof value === "number" ? value : Number(value) || 0;
          if (typeof amount === "number" && amount > threshold) {
            results.push({
              condition: key,
              met: false,
              detail: `Amount ${amount} exceeds threshold ${threshold} — escalation required`,
            });
          } else {
            results.push({
              condition: key,
              met: true,
              detail: `Within threshold (${threshold})`,
            });
          }
        } else if (key === "payout_within_authority") {
          if (typeof value === "object" && value !== null) {
            const limits = value as Record<string, number>;
            const limit = limits[request.role] ?? 0;
            const amount = (ctx.amount ?? ctx.payout_amount ?? 0) as number;
            if (typeof amount === "number" && typeof limit === "number") {
              if (amount > limit) {
                results.push({
                  condition: key,
                  met: false,
                  detail: `Amount ${amount} exceeds ${request.role} limit of ${limit}`,
                });
              } else {
                results.push({
                  condition: key,
                  met: true,
                  detail: `Within ${request.role} limit (${limit})`,
                });
              }
            } else {
              results.push({
                condition: key,
                met: true,
                detail: "No amount to check",
              });
            }
          } else {
            results.push({
              condition: key,
              met: true,
              detail: "Checked",
            });
          }
        } else if (value === "required" || value === true) {
          const ctxVal = ctx[key];
          const met = Boolean(ctxVal);
          results.push({
            condition: key,
            met,
            detail: met ? "Present in context" : "Missing or false in context",
          });
        } else if (Array.isArray(value)) {
          const ctxVal = ctx[key] ?? "";
          const met = value.includes(ctxVal);
          results.push({
            condition: key,
            met,
            detail: met
              ? `Value '${ctxVal}' in allowed: ${JSON.stringify(value)}`
              : `Value '${ctxVal}' not in allowed: ${JSON.stringify(value)}`,
          });
        } else if (typeof value === "string") {
          const ctxVal = String(ctx[key] ?? "");
          const met = ctxVal === value;
          results.push({
            condition: key,
            met,
            detail: `Expected '${value}', got '${ctxVal}'`,
          });
        } else {
          results.push({
            condition: key,
            met: true,
            detail: "Condition accepted",
          });
        }
      }
    }

    return results;
  }

  private hasEscalationTrigger(conditions: ConditionResult[]): boolean {
    for (const c of conditions) {
      if (!c.met) {
        const lower = c.detail.toLowerCase();
        if (
          lower.includes("escalation") ||
          lower.includes("threshold") ||
          lower.includes("exceeds")
        ) {
          return true;
        }
      }
    }
    return false;
  }

  check(request: WarrantRequest): WarrantResponse {
    const timestamp = request.timestamp ?? new Date();

    // Step 1: Find matching warrant
    const warrant = this.findMatchingWarrant(
      request.action,
      request.role,
      request.dataType
    );

    // Step 2: No match → NO_WARRANT
    if (!warrant) {
      const response: WarrantResponse = {
        decision: Decision.NO_WARRANT,
        conditionsEvaluated: [],
        auditHash: "",
        previousHash: "",
      };
      this.recordAndNotify(response, request);
      return response;
    }

    // Step 3: Check expiry
    if (timestamp > warrant.validUntil || timestamp < warrant.validFrom) {
      const response: WarrantResponse = {
        decision: Decision.EXPIRED,
        warrantId: warrant.id,
        authority: {
          issuer: warrant.issuer,
          type: warrant.id,
          issued: warrant.validFrom.toISOString(),
          expires: warrant.validUntil.toISOString(),
          scope: warrant.actions,
        },
        conditionsEvaluated: [],
        auditHash: "",
        previousHash: "",
      };
      this.recordAndNotify(response, request);
      return response;
    }

    // Step 4: Evaluate conditions
    const conditions = this.evaluateConditions(warrant, request);
    const failed = conditions.filter((c) => !c.met);

    const authority: WarrantAuthority = {
      issuer: warrant.issuer,
      type: warrant.id,
      issued: warrant.validFrom.toISOString(),
      expires: warrant.validUntil.toISOString(),
      scope: warrant.actions,
    };

    // Step 5: Escalation triggers
    if (failed.length > 0 && this.hasEscalationTrigger(conditions)) {
      const response: WarrantResponse = {
        decision: Decision.ESCALATE,
        warrantId: warrant.id,
        authority,
        conditionsEvaluated: conditions,
        auditHash: "",
        previousHash: "",
      };
      this.recordAndNotify(response, request);
      return response;
    }

    // Step 6: Failed conditions → DENIED
    if (failed.length > 0) {
      const response: WarrantResponse = {
        decision: Decision.DENIED,
        warrantId: warrant.id,
        authority,
        conditionsEvaluated: conditions,
        auditHash: "",
        previousHash: "",
      };
      this.recordAndNotify(response, request);
      return response;
    }

    // Step 7: AUTHORIZED
    this._executionCount++;
    let trustElevation: TrustElevation | undefined;
    if (this._executionCount >= 50) {
      trustElevation = { eligible: true, newLevel: 2 };
    } else if (this._executionCount >= 10) {
      trustElevation = { eligible: true, newLevel: 1 };
    }

    const response: WarrantResponse = {
      decision: Decision.AUTHORIZED,
      warrantId: warrant.id,
      authority,
      conditionsEvaluated: conditions,
      auditHash: "",
      previousHash: "",
      trustElevation,
    };
    this.recordAndNotify(response, request);
    return response;
  }

  private recordAndNotify(
    response: WarrantResponse,
    request: WarrantRequest
  ): void {
    const record = this._audit.record(
      response,
      request.agentId,
      request.action,
      request.correlationId
    );
    response.auditHash = record.recordHash;
    response.previousHash = record.previousHash;

    if (this._onDecision) this._onDecision(response);
    if (response.decision === Decision.AUTHORIZED && this._onAuthorized) {
      this._onAuthorized(response);
    } else if (response.decision === Decision.DENIED && this._onDenied) {
      this._onDenied(response);
    } else if (response.decision === Decision.ESCALATE && this._onEscalate) {
      this._onEscalate(response);
    }
  }
}
