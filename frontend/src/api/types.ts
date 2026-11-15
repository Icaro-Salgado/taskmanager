// Payloads of the REST API under /api/v1, written once and shared by every feature.

export type Role = "leader" | "member";

export type TaskStatus = "todo" | "in_progress" | "blocked" | "done" | "canceled";

/** Every error leaves the API in this shape (backend/apps/core/exception_handler.py). */
export interface ApiErrorBody {
  code: string;
  message: string;
  /** Field errors for invalid input ({field: [messages]}), otherwise null. */
  details: Record<string, string[]> | null;
}

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface TokenPair {
  access: string;
  refresh: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  is_admin: boolean;
}

export interface UserRef {
  id: number;
  email: string;
}

export interface Team {
  id: number;
  name: string;
  archive_after_days: number;
  /** The caller's role in the team; null for an admin who is not a member. */
  my_role: Role | null;
}

export interface Member {
  user_id: number;
  email: string;
  role: Role;
  joined_at: string;
}

export interface Task {
  id: number;
  team: number;
  title: string;
  description: string;
  status: TaskStatus;
  assignee: UserRef | null;
  created_by: UserRef;
  /** A date (YYYY-MM-DD) or null. */
  due_date: string | null;
  completed_at: string | null;
  is_overdue: boolean;
  can_edit: boolean;
  can_delete: boolean;
  created_at: string;
  updated_at: string;
}

export interface TaskCreate {
  team: number;
  title: string;
  description: string;
  status: TaskStatus;
  assignee: number | null;
  due_date: string | null;
}

export type TaskUpdate = Partial<Omit<TaskCreate, "team">>;

/** Query parameters of GET /tasks. Unset keys are left out of the query string. */
export interface TaskListParams {
  team?: number;
  status?: TaskStatus;
  /** A user id, or "none" for unassigned tasks. */
  assignee?: string;
  due_after?: string;
  due_before?: string;
  overdue?: boolean;
  archived?: boolean;
  page?: number;
  page_size?: number;
}

export interface Notification {
  id: number;
  team: number;
  task: number | null;
  message: string;
  created_at: string;
  read_at: string | null;
}
