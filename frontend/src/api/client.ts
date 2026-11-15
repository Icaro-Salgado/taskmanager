// The one place that talks HTTP to the API: adds the access token, refreshes it when needed and
// turns every error answer into an ApiError carrying the API's {code, message, details}.

import { clearTokens, getAccessToken, getRefreshToken, isExpiring, storeTokens } from "./tokens";
import type { ApiErrorBody, TokenPair } from "./types";

const BASE_URL = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, string[]> | null;

  constructor(status: number, body: ApiErrorBody) {
    super(body.message);
    this.name = "ApiError";
    this.status = status;
    this.code = body.code;
    this.details = body.details;
  }
}

type QueryValue = string | number | boolean | undefined;

export interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  query?: object;
  /** False for the token endpoints: no Authorization header, no refresh on 401. */
  auth?: boolean;
  signal?: AbortSignal;
}

let onSessionExpired: () => void = () => undefined;

/** Called when the session cannot be renewed (the refresh token was refused). */
export function setSessionExpiredHandler(handler: () => void): void {
  onSessionExpired = handler;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const auth = options.auth ?? true;
  if (!auth) return parse<T>(await send(path, options, null));

  if (isExpiring(getAccessToken(), Date.now()) && getRefreshToken()) {
    // No access token yet (after a reload) or about to expire: renew first, sparing a 401.
    if (!(await refreshSession())) throw sessionExpiredError();
  }
  const sentWith = getAccessToken();
  let response = await send(path, options, sentWith);
  if (response.status === 401 && getRefreshToken()) {
    // Another request may have renewed the token while this one was in flight; if not, renew.
    const renewed = getAccessToken() !== sentWith || (await refreshSession());
    if (renewed) response = await send(path, options, getAccessToken());
  }
  return parse<T>(response);
}

function sessionExpiredError(): ApiError {
  return new ApiError(401, {
    code: "session_expired",
    message: "Your session has expired. Please log in again.",
    details: null,
  });
}

let refreshing: Promise<boolean> | null = null;

/**
 * Renews the access token. Concurrent callers share one request: the API rotates the refresh token
 * and blacklists the old one, so a second parallel refresh would be refused and end the session.
 * Resolves false, and ends the session, when the API refuses the refresh token.
 */
export function refreshSession(): Promise<boolean> {
  refreshing ??= doRefresh().finally(() => {
    refreshing = null;
  });
  return refreshing;
}

async function doRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  const response = await send("/auth/token/refresh", { method: "POST", body: { refresh } }, null);
  if (!response.ok) {
    clearTokens();
    onSessionExpired();
    return false;
  }
  const tokens = (await response.json()) as TokenPair;
  storeTokens(tokens.access, tokens.refresh);
  return true;
}

function send(path: string, options: RequestOptions, token: string | null): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(BASE_URL + path + queryString(options.query), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });
}

/** "?a=1&b=x" from the defined values, or "" when there are none. */
export function queryString(query: object | undefined): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query) as [string, QueryValue][]) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

async function parse<T>(response: Response): Promise<T> {
  if (response.ok) {
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }
  throw new ApiError(response.status, await errorBody(response));
}

async function errorBody(response: Response): Promise<ApiErrorBody> {
  try {
    const body = (await response.json()) as Partial<ApiErrorBody>;
    if (typeof body.message === "string" && body.message) {
      return { code: body.code ?? "error", message: body.message, details: body.details ?? null };
    }
  } catch {
    // Not JSON (for example a proxy error page): fall through to a generic message.
  }
  return { code: "error", message: `The server answered ${response.status}.`, details: null };
}
