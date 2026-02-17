/** Core data models for OpenWarrant. */

export enum Decision {
  AUTHORIZED = "AUTHORIZED",
  DENIED = "DENIED",
  ESCALATE = "ESCALATE",
  NO_WARRANT = "NO_WARRANT",
  EXPIRED = "EXPIRED",
}

export interface Warrant {
  id: string;
  issuer: string;
  signature: string;
  roles: string[];
  actions: string[];
  dataTypes: string[];
  conditions: Record<string, unknown>[];
  validFrom: Date;
  validUntil: Date;
  trustLevelRequired: number;
  auditRequired: boolean;
  escalationTarget: string;
  notes: string;
}

export interface WarrantRequest {
  agentId: string;
  action: string;
  role: string;
  dataType: string;
  context: Record<string, unknown>;
  timestamp?: Date;
  correlationId?: string;
}

export interface ConditionResult {
  condition: string;
  met: boolean;
  detail: string;
}

export interface WarrantAuthority {
  issuer: string;
  type: string;
  issued: string;
  expires: string;
  scope: string[];
}

export interface TrustElevation {
  eligible: boolean;
  newLevel?: number;
}

export interface WarrantResponse {
  decision: Decision;
  warrantId?: string;
  authority?: WarrantAuthority;
  conditionsEvaluated: ConditionResult[];
  auditHash: string;
  previousHash: string;
  trustElevation?: TrustElevation;
}
