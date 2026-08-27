export const PROVIDER_PAGE_STATES = ['READY', 'AUTH_REQUIRED', 'BLOCKED', 'UNKNOWN'] as const;
export type ProviderPageState = (typeof PROVIDER_PAGE_STATES)[number];

export type ProviderStateReason =
  | 'COMPOSER_READY'
  | 'LOGIN_REQUIRED'
  | 'RATE_LIMIT'
  | 'PROTECTION_CHALLENGE'
  | 'ACCOUNT_BLOCKED'
  | 'ACCESS_DENIED'
  | 'UNRECOGNIZED_PAGE';

export interface ProviderStateObservation {
  state: ProviderPageState;
  reason: ProviderStateReason;
  url: string;
  observedAt: string;
  signals: readonly string[];
  operatorActionRequired: boolean;
}

export interface ProviderPageSnapshot {
  url: string;
  title: string;
  bodyText: string;
  visibleSelectors: readonly string[];
}
