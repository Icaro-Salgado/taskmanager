import { errorMessage } from "../lib/errors";

/** Shows the API's message for a failed request; renders nothing when there is no error. */
export function ErrorMessage({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
      {errorMessage(error)}
    </p>
  );
}
