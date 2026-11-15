import { createContext, useContext } from "react";

import type { CurrentUser } from "../../api/types";

export type AuthState =
  | { status: "loading" | "anonymous"; user: null; login: LoginFn; logout: LogoutFn }
  | { status: "authenticated"; user: CurrentUser; login: LoginFn; logout: LogoutFn };

type LoginFn = (email: string, password: string) => Promise<void>;
type LogoutFn = () => Promise<void>;

export const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside AuthProvider");
  return auth;
}

/** The logged-in user; only for components rendered behind RequireAuth. */
export function useCurrentUser(): CurrentUser {
  const auth = useAuth();
  if (!auth.user) throw new Error("useCurrentUser needs a logged-in user");
  return auth.user;
}
