export interface MemoryEntry {
  spoken: string;
  target: string;
  scope: "global" | "workspace" | "personal";
  confidence: number;
  source: string;
}

export interface AppliedReplacement extends MemoryEntry {
  count: number;
}

export interface RecoveryResult {
  original: string;
  recovered: string;
  changed: boolean;
  applied: AppliedReplacement[];
}

const VALID_SCOPES = new Set(["global", "workspace", "personal"]);

export function parseMemoryEntries(payload: unknown): MemoryEntry[] {
  if (
    typeof payload !== "object" ||
    payload === null ||
    Array.isArray(payload)
  ) {
    throw new Error("memory file must contain a JSON object");
  }

  const record = payload as Record<string, unknown>;
  if (record.version !== 1) {
    throw new Error("memory file field 'version' must be 1");
  }
  if (!Array.isArray(record.entries)) {
    throw new Error("memory file field 'entries' must be a list");
  }

  return record.entries
    .map((entry, index) => parseMemoryEntry(entry, index))
    .sort((left, right) => right.spoken.length - left.spoken.length);
}

export function recoverText(
  text: string,
  entries: MemoryEntry[],
  minConfidence = 0.8,
): RecoveryResult {
  if (minConfidence < 0 || minConfidence > 1) {
    throw new Error("--min-confidence must be between 0 and 1");
  }

  let recovered = text;
  const applied: AppliedReplacement[] = [];

  for (const entry of entries) {
    if (entry.confidence < minConfidence) {
      continue;
    }

    const pattern = spokenPattern(entry.spoken);
    let count = 0;
    recovered = recovered.replace(pattern, () => {
      count += 1;
      return entry.target;
    });

    if (count > 0) {
      applied.push({ ...entry, count });
    }
  }

  return {
    original: text,
    recovered,
    changed: text !== recovered,
    applied,
  };
}

function parseMemoryEntry(value: unknown, index: number): MemoryEntry {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`memory entry ${index} must be an object`);
  }
  const entry = value as Record<string, unknown>;
  const spoken = requireNonEmptyString(entry.spoken, "spoken", index);
  const target = requireNonEmptyString(entry.target, "target", index);
  const scope = requireScope(entry.scope ?? "workspace", index);
  const confidence = requireConfidence(entry.confidence ?? 1, index);
  const source = requireNonEmptyString(
    entry.source ?? "manual",
    "source",
    index,
  );

  return { spoken, target, scope, confidence, source };
}

function requireNonEmptyString(
  value: unknown,
  field: string,
  index: number,
): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(
      `memory entry ${index} field '${field}' must be a non-empty string`,
    );
  }

  return value.trim();
}

function requireScope(value: unknown, index: number): MemoryEntry["scope"] {
  const scope = requireNonEmptyString(value, "scope", index);
  if (!VALID_SCOPES.has(scope)) {
    throw new Error(
      `memory entry ${index} field 'scope' must be one of ${JSON.stringify(Array.from(VALID_SCOPES).sort())}`,
    );
  }

  return scope as MemoryEntry["scope"];
}

function requireConfidence(value: unknown, index: number): number {
  if (typeof value !== "number") {
    throw new Error(
      `memory entry ${index} field 'confidence' must be a number`,
    );
  }
  if (value < 0 || value > 1) {
    throw new Error(
      `memory entry ${index} field 'confidence' must be between 0 and 1`,
    );
  }

  return value;
}

function spokenPattern(spoken: string): RegExp {
  return new RegExp(spoken.split(/\s+/u).map(escapeRegExp).join("\\s*"), "gu");
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
