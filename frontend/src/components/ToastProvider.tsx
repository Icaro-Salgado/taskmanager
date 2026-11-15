import { useCallback, useMemo, useState, type ReactNode } from "react";

import { ToastContext, type ToastAction, type ToastApi } from "./toastContext";

interface Toast {
  id: number;
  message: string;
  action?: ToastAction;
}

let nextId = 1;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback<ToastApi["show"]>(
    (message, options = {}) => {
      const id = nextId++;
      setToasts((current) => [...current, { id, message, action: options.action }]);
      window.setTimeout(() => dismiss(id), options.durationMs ?? 5000);
    },
    [dismiss],
  );

  const api = useMemo(() => ({ show }), [show]);

  return (
    <ToastContext value={api}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-4 z-50 flex flex-col items-center gap-2 px-4"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="pointer-events-auto flex w-full max-w-md items-center justify-between gap-3 rounded-md bg-slate-900 px-4 py-3 text-sm text-white shadow-lg"
          >
            <span>{toast.message}</span>
            <div className="flex shrink-0 gap-2">
              {toast.action && (
                <button
                  type="button"
                  className="rounded px-2 py-1 font-semibold text-sky-300 hover:bg-slate-800"
                  onClick={() => {
                    toast.action?.onClick();
                    dismiss(toast.id);
                  }}
                >
                  {toast.action.label}
                </button>
              )}
              <button
                type="button"
                aria-label="Dismiss"
                className="rounded px-2 py-1 text-slate-300 hover:bg-slate-800"
                onClick={() => dismiss(toast.id)}
              >
                ×
              </button>
            </div>
          </div>
        ))}
      </div>
    </ToastContext>
  );
}
