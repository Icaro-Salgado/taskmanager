import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, queryString, setSessionExpiredHandler } from "./client";
import { clearTokens, getAccessToken, getRefreshToken, isExpiring, storeTokens } from "./tokens";

/** A JWT-shaped token whose payload carries `exp` (seconds); the signature is never checked here. */
function jwt(name: string, expiresInSeconds = 900): string {
  const payload = btoa(JSON.stringify({ exp: Math.floor(Date.now() / 1000) + expiresInSeconds }));
  return `header.${payload.replace(/=+$/, "")}.${name}`;
}

function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const unauthorized = () =>
  json(401, { code: "token_not_valid", message: "Token is invalid", details: null });

/** Records each request as "METHOD path" plus the bearer token it carried. */
interface Call {
  url: string;
  token: string | null;
  body: unknown;
}

let calls: Call[];
let fetchMock: ReturnType<typeof vi.fn>;

function stubFetch(handler: (call: Call) => Response | Promise<Response>) {
  fetchMock = vi.fn(async (url: string, init: RequestInit) => {
    const headers = init.headers as Record<string, string>;
    const call: Call = {
      url,
      token: headers.Authorization?.replace("Bearer ", "") ?? null,
      body: init.body ? JSON.parse(init.body as string) : undefined,
    };
    calls.push(call);
    return handler(call);
  });
  vi.stubGlobal("fetch", fetchMock);
}

beforeEach(() => {
  const store = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => store.set(key, value),
    removeItem: (key: string) => store.delete(key),
  });
  calls = [];
  clearTokens();
  setSessionExpiredHandler(() => undefined);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("token refresh", () => {
  it("shares one refresh between concurrent 401s, retries each request and stores the rotated token", async () => {
    const oldAccess = jwt("old");
    const newAccess = jwt("new");
    storeTokens(oldAccess, "refresh-1");
    let releaseRefresh: () => void = () => undefined;
    const refreshAnswered = new Promise<void>((resolve) => (releaseRefresh = resolve));

    stubFetch(async (call) => {
      if (call.url.endsWith("/auth/token/refresh")) {
        await refreshAnswered; // hold the refresh so both requests are waiting for it
        return json(200, { access: newAccess, refresh: "refresh-2" });
      }
      if (call.token === oldAccess) return unauthorized();
      return json(200, { url: call.url });
    });

    const first = apiRequest<{ url: string }>("/teams");
    const second = apiRequest<{ url: string }>("/tasks");
    await vi.waitFor(() => expect(calls.filter((c) => c.url.includes("refresh"))).toHaveLength(1));
    releaseRefresh();

    await expect(first).resolves.toEqual({ url: "/api/v1/teams" });
    await expect(second).resolves.toEqual({ url: "/api/v1/tasks" });
    const refreshCalls = calls.filter((c) => c.url.endsWith("/auth/token/refresh"));
    expect(refreshCalls).toHaveLength(1);
    expect(refreshCalls[0]?.body).toEqual({ refresh: "refresh-1" });
    expect(calls.filter((c) => c.token === newAccess).map((c) => c.url)).toEqual([
      "/api/v1/teams",
      "/api/v1/tasks",
    ]);
    expect(getRefreshToken()).toBe("refresh-2");
    expect(getAccessToken()).toBe(newAccess);
  });

  it("ends the session when the refresh token is refused", async () => {
    storeTokens(jwt("old"), "refresh-1");
    const onExpired = vi.fn();
    setSessionExpiredHandler(onExpired);
    stubFetch((call) =>
      call.url.endsWith("/auth/token/refresh")
        ? json(401, { code: "token_not_valid", message: "Token is blacklisted", details: null })
        : unauthorized(),
    );

    const failure = apiRequest("/teams");

    await expect(failure).rejects.toMatchObject({ status: 401 });
    expect(onExpired).toHaveBeenCalledOnce();
    expect(getRefreshToken()).toBeNull();
    expect(getAccessToken()).toBeNull();
    // The original request, one refresh, and no second retry.
    expect(calls.map((c) => c.url)).toEqual(["/api/v1/teams", "/api/v1/auth/token/refresh"]);
  });

  it("retries with the token another tab stored meanwhile instead of ending the session", async () => {
    storeTokens(jwt("old"), "refresh-1");
    const onExpired = vi.fn();
    setSessionExpiredHandler(onExpired);
    stubFetch((call) => {
      if (call.url.endsWith("/auth/token/refresh")) {
        const { refresh } = call.body as { refresh: string };
        if (refresh === "refresh-2") return json(200, { access: jwt("new"), refresh: "refresh-3" });
        // Another tab rotated refresh-1 a moment ago and stored refresh-2.
        localStorage.setItem("taskmanager.refresh", "refresh-2");
        return json(401, { code: "token_not_valid", message: "Token is blacklisted", details: null });
      }
      return call.token?.endsWith(".new") ? json(200, []) : unauthorized();
    });

    await expect(apiRequest("/teams")).resolves.toEqual([]);
    expect(onExpired).not.toHaveBeenCalled();
    expect(getRefreshToken()).toBe("refresh-3");
  });

  it("renews first when there is no access token yet (after a reload), sparing a 401", async () => {
    localStorage.setItem("taskmanager.refresh", "refresh-1");
    const access = jwt("fresh");
    stubFetch((call) =>
      call.url.endsWith("/auth/token/refresh")
        ? json(200, { access, refresh: "refresh-2" })
        : json(200, { ok: true }),
    );

    await apiRequest("/auth/me");

    expect(calls.map((c) => [c.url, c.token])).toEqual([
      ["/api/v1/auth/token/refresh", null],
      ["/api/v1/auth/me", access],
    ]);
  });

  it("retries without refreshing again when another request already renewed the token", async () => {
    const oldAccess = jwt("old");
    const newAccess = jwt("new");
    storeTokens(oldAccess, "refresh-1");
    stubFetch((call) => {
      if (call.token === oldAccess) {
        // While this request was in flight, another one renewed the session.
        storeTokens(newAccess, "refresh-2");
        return unauthorized();
      }
      return json(200, { ok: true });
    });

    await apiRequest("/teams");

    expect(calls.map((c) => c.token)).toEqual([oldAccess, newAccess]);
  });

  it("never refreshes for the token endpoints (a wrong password is a plain 401)", async () => {
    storeTokens(jwt("old"), "refresh-1");
    stubFetch(() =>
      json(401, {
        code: "no_active_account",
        message: "No active account found with the given credentials",
        details: null,
      }),
    );

    const login = apiRequest("/auth/token", { method: "POST", body: {}, auth: false });

    await expect(login).rejects.toThrow("No active account found with the given credentials");
    expect(calls).toHaveLength(1);
    expect(calls[0]?.token).toBeNull();
  });
});

describe("errors", () => {
  it("carries the API's code, message and field details", async () => {
    storeTokens(jwt("a"), "r");
    stubFetch(() =>
      json(400, { code: "invalid", message: "Invalid input.", details: { title: ["Required."] } }),
    );

    const error = await apiRequest("/tasks", { method: "POST", body: {} }).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 400,
      code: "invalid",
      message: "Invalid input.",
      details: { title: ["Required."] },
    });
  });

  it("falls back to a generic message when the answer is not JSON", async () => {
    storeTokens(jwt("a"), "r");
    stubFetch(() => new Response("<html>Bad gateway</html>", { status: 502 }));

    await expect(apiRequest("/teams")).rejects.toThrow("The server answered 502.");
  });
});

describe("helpers", () => {
  it("builds a query string from the defined values only", () => {
    expect(queryString({ team: 3, status: "todo", overdue: true, assignee: undefined })).toBe(
      "?team=3&status=todo&overdue=true",
    );
    expect(queryString({ due_after: "" })).toBe("");
    expect(queryString(undefined)).toBe("");
  });

  it("tells when a token is missing, malformed or about to expire", () => {
    const now = Date.now();
    expect(isExpiring(null, now)).toBe(true);
    expect(isExpiring("not-a-jwt", now)).toBe(true);
    expect(isExpiring(jwt("x", 600), now)).toBe(false);
    expect(isExpiring(jwt("x", 10), now)).toBe(true); // within the 30-second margin
    expect(isExpiring(jwt("x", -60), now)).toBe(true);
  });
});
