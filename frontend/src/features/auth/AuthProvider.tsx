import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { setSessionExpiredHandler } from "../../api/client";
import { authApi } from "../../api/endpoints";
import { clearTokens, getRefreshToken, storeTokens } from "../../api/tokens";
import { AuthContext, type AuthState } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  // A stored refresh token means a session may still be alive; /auth/me tells for sure.
  const [hasSession, setHasSession] = useState(() => getRefreshToken() !== null);

  const me = useQuery({
    queryKey: ["auth", "me"],
    queryFn: authApi.me,
    enabled: hasSession,
    staleTime: Infinity,
    retry: false,
  });

  const endSession = useCallback(() => {
    clearTokens();
    setHasSession(false);
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setSessionExpiredHandler(endSession);
  }, [endSession]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await authApi.login(email, password);
      storeTokens(tokens.access, tokens.refresh);
      // Forget a failed /auth/me from before, so it is asked again with the new tokens.
      await queryClient.resetQueries({ queryKey: ["auth", "me"] });
      setHasSession(true);
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    const refresh = getRefreshToken();
    try {
      // Blacklists the refresh token, so a stolen copy is useless after logout.
      if (refresh) await authApi.logout(refresh);
    } catch {
      // The local session ends anyway; the token expires on its own.
    }
    endSession();
  }, [endSession]);

  const value = useMemo<AuthState>(() => {
    if (!hasSession) return { status: "anonymous", user: null, login, logout };
    if (me.data) return { status: "authenticated", user: me.data, login, logout };
    if (me.isError) return { status: "anonymous", user: null, login, logout };
    return { status: "loading", user: null, login, logout };
  }, [hasSession, me.data, me.isError, login, logout]);

  return <AuthContext value={value}>{children}</AuthContext>;
}
