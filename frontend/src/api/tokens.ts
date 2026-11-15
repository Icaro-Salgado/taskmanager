// Where the session's tokens live.
//
// Trade-off (decided by the owner): the access token is kept only in memory, so no script can read
// it from storage; the refresh token is kept in localStorage so a page reload keeps the session.
// An XSS bug could read the refresh token from localStorage. What limits the damage: the API
// rotates refresh tokens and blacklists the old one on every refresh and on logout, and an access
// token lasts 15 minutes. The safer alternative, an httpOnly cookie, needs CSRF handling the API
// does not have.

const REFRESH_KEY = "taskmanager.refresh";

let accessToken: string | null = null;

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function storeTokens(access: string, refresh: string): void {
  accessToken = access;
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  accessToken = null;
  localStorage.removeItem(REFRESH_KEY);
}

/**
 * True when the JWT is missing, unreadable or expires within `marginSeconds`. Only used to refresh
 * ahead of time and spare a 401; the server still decides whether a token is valid.
 */
export function isExpiring(token: string | null, nowMs: number, marginSeconds = 30): boolean {
  if (!token) return true;
  const payload = token.split(".")[1];
  if (!payload) return true;
  try {
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const claims: unknown = JSON.parse(atob(base64));
    if (typeof claims !== "object" || claims === null || !("exp" in claims)) return true;
    const exp = claims.exp;
    return typeof exp !== "number" || exp * 1000 - marginSeconds * 1000 <= nowMs;
  } catch {
    return true;
  }
}
