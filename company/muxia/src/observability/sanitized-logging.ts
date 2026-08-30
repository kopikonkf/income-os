const SENSITIVE_KEY = /(?:auth(?:orization|entication|body|header)?|bearer|cookie|credential|csrf|jwt|localstorage|password|private[_-]?key|secret|session(?:id|storage)?|set-cookie|token)/i;
const SENSITIVE_VALUE = /(?:\bBearer\s+[A-Za-z0-9._~+\/-]+=*|\bBasic\s+[A-Za-z0-9+/]+=*|\b(?:sk|sess|pat)[_-][A-Za-z0-9_-]{12,}|\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|(?:^|[;?&\s])(?:access_token|auth|authorization|cookie|password|refresh_token|session|token)=\S+)/i;

export const REDACTED = '[REDACTED]';

export type SanitizedLogValue =
  | null
  | boolean
  | number
  | string
  | SanitizedLogValue[]
  | { [key: string]: SanitizedLogValue };

function sanitizeString(value: string): string {
  if (SENSITIVE_VALUE.test(value)) return REDACTED;
  return value.length <= 512 ? value : `${value.slice(0, 509)}...`;
}

function sanitize(
  value: unknown,
  seen: WeakSet<object>,
  depth: number,
): SanitizedLogValue {
  if (depth > 8) return '[MAX_DEPTH]';
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'number') return Number.isFinite(value) ? value : String(value);
  if (typeof value === 'string') return sanitizeString(value);
  if (typeof value === 'bigint' || typeof value === 'symbol' || typeof value === 'function' || value === undefined) {
    return String(value);
  }
  if (value instanceof Error) {
    return {
      name: sanitizeString(value.name),
      code: safeDiagnosticCode(value.message),
    };
  }
  if (seen.has(value)) return '[CIRCULAR]';
  seen.add(value);
  if (Array.isArray(value)) return value.map((item) => sanitize(item, seen, depth + 1));

  const result: Record<string, SanitizedLogValue> = {};
  for (const [key, child] of Object.entries(value as Record<string, unknown>)) {
    result[key] = SENSITIVE_KEY.test(key) ? REDACTED : sanitize(child, seen, depth + 1);
  }
  return result;
}

export function sanitizeLogEvent(value: unknown): SanitizedLogValue {
  return sanitize(value, new WeakSet<object>(), 0);
}

export function safeDiagnosticCode(detail: unknown): string {
  const raw = detail instanceof Error ? detail.message : String(detail);
  const candidate = raw.split(':', 1)[0]?.trim().toUpperCase() ?? '';
  return /^[A-Z][A-Z0-9_]{1,63}$/.test(candidate) ? candidate : 'INTERNAL_ERROR';
}
