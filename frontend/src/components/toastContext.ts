import { createContext, useContext } from "react";

export interface ToastAction {
  label: string;
  onClick: () => void;
}

export interface ToastApi {
  /** Shows a message for `durationMs`, optionally with one action button (for example Undo). */
  show: (message: string, options?: { action?: ToastAction; durationMs?: number }) => void;
}

export const ToastContext = createContext<ToastApi | null>(null);

export function useToast(): ToastApi {
  const toast = useContext(ToastContext);
  if (!toast) throw new Error("useToast must be used inside ToastProvider");
  return toast;
}
