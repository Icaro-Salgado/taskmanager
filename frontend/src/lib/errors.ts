import { ApiError } from "../api/client";

/** The text to show for a failed request: the API's own message when there is one. */
export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return `Not allowed: ${error.message}`;
    if (error.status === 409) return `Conflict: ${error.message}`;
    return error.message;
  }
  if (error instanceof TypeError) return "Could not reach the server. Check your connection.";
  return "Something went wrong.";
}

/** Field errors of an invalid-input answer (HTTP 400), keyed by field name. */
export function fieldErrors(error: unknown): Record<string, string[]> {
  return error instanceof ApiError && error.details ? error.details : {};
}

export function isNotFound(error: unknown): boolean {
  return error instanceof ApiError && error.status === 404;
}
