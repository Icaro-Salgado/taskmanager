// Every API endpoint the app calls, typed. Features use these through their query hooks.

import { apiRequest } from "./client";
import type {
  CurrentUser,
  Member,
  Notification,
  Page,
  Role,
  Task,
  TaskCreate,
  TaskListParams,
  TaskUpdate,
  Team,
  TokenPair,
} from "./types";

export const authApi = {
  login: (email: string, password: string) =>
    apiRequest<TokenPair>("/auth/token", {
      method: "POST",
      body: { email, password },
      auth: false,
    }),
  logout: (refresh: string) =>
    apiRequest<unknown>("/auth/logout", { method: "POST", body: { refresh }, auth: false }),
  me: () => apiRequest<CurrentUser>("/auth/me"),
};

export const teamsApi = {
  list: () => apiRequest<Team[]>("/teams"),
  members: (teamId: number) => apiRequest<Member[]>(`/teams/${teamId}/members`),
  addMember: (teamId: number, email: string) =>
    apiRequest<Member>(`/teams/${teamId}/members`, { method: "POST", body: { email } }),
  changeRole: (teamId: number, userId: number, role: Role) =>
    apiRequest<Member>(`/teams/${teamId}/members/${userId}`, {
      method: "PATCH",
      body: { role },
    }),
  removeMember: (teamId: number, userId: number) =>
    apiRequest<unknown>(`/teams/${teamId}/members/${userId}`, { method: "DELETE" }),
};

export const tasksApi = {
  list: (params: TaskListParams, signal?: AbortSignal) =>
    apiRequest<Page<Task>>("/tasks", { query: params, signal }),
  get: (taskId: number, signal?: AbortSignal) => apiRequest<Task>(`/tasks/${taskId}`, { signal }),
  create: (data: TaskCreate) => apiRequest<Task>("/tasks", { method: "POST", body: data }),
  update: (taskId: number, data: TaskUpdate) =>
    apiRequest<Task>(`/tasks/${taskId}`, { method: "PATCH", body: data }),
  remove: (taskId: number) => apiRequest<unknown>(`/tasks/${taskId}`, { method: "DELETE" }),
  reopen: (taskId: number) => apiRequest<Task>(`/tasks/${taskId}/reopen`, { method: "POST" }),
  assignSelf: (taskId: number) =>
    apiRequest<Task>(`/tasks/${taskId}/assign-self`, { method: "POST" }),
};

export const notificationsApi = {
  list: (params: { unread?: boolean; page_size?: number }) =>
    apiRequest<Page<Notification>>("/notifications", { query: params }),
  markRead: (id: number) =>
    apiRequest<Notification>(`/notifications/${id}/read`, { method: "POST" }),
};
