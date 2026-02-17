/** Load warrant definitions from YAML files. */

import * as fs from "fs";
import * as path from "path";
import type { Warrant } from "./models.js";

/**
 * Minimal YAML parser sufficient for warrant files.
 * Handles mappings, sequences, scalars, and quoted strings.
 */
function parseYamlValue(value: string): unknown {
  value = value.trim();
  if (!value) return "";

  // Remove inline comments
  const commentIdx = value.indexOf("  #");
  if (commentIdx !== -1) {
    value = value.substring(0, commentIdx).trim();
  }

  // Quoted strings
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    return value.slice(1, -1);
  }

  // Booleans
  const lower = value.toLowerCase();
  if (lower === "true" || lower === "yes") return true;
  if (lower === "false" || lower === "no") return false;
  if (lower === "null" || lower === "~") return null;

  // Numbers
  const num = Number(value);
  if (!isNaN(num) && value !== "") return num;

  return value;
}

function getIndent(line: string): number {
  return line.length - line.trimStart().length;
}

interface ParseResult {
  data: Record<string, unknown>;
  nextIndex: number;
}

interface ListResult {
  items: unknown[];
  nextIndex: number;
}

function parseBlock(
  lines: string[],
  start: number,
  baseIndent: number
): ParseResult {
  const result: Record<string, unknown> = {};
  let i = start;

  while (i < lines.length) {
    const line = lines[i];
    const stripped = line.trim();

    if (!stripped || stripped.startsWith("#") || stripped === "---") {
      i++;
      continue;
    }

    const indent = getIndent(line);
    if (indent < baseIndent) break;
    if (indent !== baseIndent) {
      if (indent < baseIndent) break;
      i++;
      continue;
    }

    if (stripped.startsWith("- ")) {
      i++;
      continue;
    }

    const match = stripped.match(/^([\w_][\w\-_]*)\s*:\s*(.*)/);
    if (!match) {
      i++;
      continue;
    }

    const key = match[1];
    let valueStr = match[2].trim();

    // Remove inline comments
    const cIdx = valueStr.indexOf("  #");
    if (cIdx !== -1) {
      valueStr = valueStr.substring(0, cIdx).trim();
    }

    if (valueStr) {
      result[key] = parseYamlValue(valueStr);
      i++;
    } else {
      let nextI = i + 1;
      while (
        nextI < lines.length &&
        (!lines[nextI].trim() || lines[nextI].trim().startsWith("#"))
      ) {
        nextI++;
      }

      if (nextI >= lines.length) {
        result[key] = null;
        i = nextI;
        continue;
      }

      const nextIndent = getIndent(lines[nextI]);
      const nextStripped = lines[nextI].trim();

      if (nextIndent <= baseIndent) {
        result[key] = null;
        i = nextI;
      } else if (nextStripped.startsWith("- ")) {
        const listResult = parseList(lines, nextI, nextIndent);
        result[key] = listResult.items;
        i = listResult.nextIndex;
      } else {
        const nested = parseBlock(lines, nextI, nextIndent);
        result[key] = nested.data;
        i = nested.nextIndex;
      }
    }
  }

  return { data: result, nextIndex: i };
}

function parseList(
  lines: string[],
  start: number,
  baseIndent: number
): ListResult {
  const items: unknown[] = [];
  let i = start;

  while (i < lines.length) {
    const line = lines[i];
    const stripped = line.trim();

    if (!stripped || stripped.startsWith("#")) {
      i++;
      continue;
    }

    const indent = getIndent(line);
    if (indent < baseIndent) break;

    if (indent === baseIndent && stripped.startsWith("- ")) {
      const itemContent = stripped.substring(2).trim();

      const mapMatch = itemContent.match(/^([\w_][\w\-_]*)\s*:\s*(.*)/);
      if (mapMatch) {
        const itemKey = mapMatch[1];
        let itemValStr = mapMatch[2].trim();
        if (itemValStr) {
          const cIdx = itemValStr.indexOf("  #");
          if (cIdx !== -1) itemValStr = itemValStr.substring(0, cIdx).trim();
          items.push({ [itemKey]: parseYamlValue(itemValStr) });
        } else {
          items.push({ [itemKey]: null });
        }
        i++;
      } else {
        if (itemContent.startsWith("[") && itemContent.endsWith("]")) {
          const inner = itemContent.slice(1, -1);
          items.push(
            inner
              .split(",")
              .map((x) => parseYamlValue(x.trim()))
              .filter((x) => x !== "")
          );
        } else {
          items.push(parseYamlValue(itemContent));
        }
        i++;
      }
    } else if (indent > baseIndent) {
      i++;
    } else {
      break;
    }
  }

  return { items, nextIndex: i };
}

export function parseYaml(text: string): Record<string, unknown> {
  const lines = text.split("\n");
  return parseBlock(lines, 0, 0).data;
}

function parseDateTime(value: string): Date {
  let v = value.replace(/['"]/g, "");
  return new Date(v);
}

function extractWarrant(data: Record<string, unknown>): Warrant {
  const w = (data.warrant ?? data) as Record<string, unknown>;

  const who = (w.who_can_act ?? {}) as Record<string, unknown>;
  const roles = (who.roles as string[]) ?? [];

  const what = (w.what_they_can_do ?? {}) as Record<string, unknown>;
  const actions = (what.actions as string[]) ?? [];
  const dataTypes = (what.data_types as string[]) ?? [];

  const rawConditions = (w.under_what_conditions ?? []) as Record<
    string,
    unknown
  >[];
  const conditions: Record<string, unknown>[] = Array.isArray(rawConditions)
    ? rawConditions.filter((c) => typeof c === "object" && c !== null)
    : [];

  return {
    id: String(w.id ?? ""),
    issuer: String(w.issuer ?? ""),
    signature: String(w.signature ?? ""),
    roles,
    actions,
    dataTypes,
    conditions,
    validFrom: parseDateTime(String(w.valid_from ?? "2026-01-01T00:00:00Z")),
    validUntil: parseDateTime(String(w.valid_until ?? "2026-12-31T23:59:59Z")),
    trustLevelRequired: Number(w.trust_level_required ?? 0),
    auditRequired: Boolean(w.audit_required ?? true),
    escalationTarget: String(w.escalation_target ?? ""),
    notes: String(w.notes ?? ""),
  };
}

export function loadWarrantFile(filePath: string): Warrant {
  const text = fs.readFileSync(filePath, "utf-8");
  const data = parseYaml(text);
  return extractWarrant(data);
}

export function loadWarrantDir(dirPath: string): Warrant[] {
  const warrants: Warrant[] = [];

  if (!fs.existsSync(dirPath) || !fs.statSync(dirPath).isDirectory()) {
    throw new Error(`Warrant directory not found: ${dirPath}`);
  }

  const files = fs.readdirSync(dirPath).sort();
  for (const file of files) {
    if (file.endsWith(".yaml") || file.endsWith(".yml")) {
      try {
        const warrant = loadWarrantFile(path.join(dirPath, file));
        warrants.push(warrant);
      } catch {
        continue;
      }
    }
  }

  return warrants;
}
