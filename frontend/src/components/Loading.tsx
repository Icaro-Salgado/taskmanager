export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <p role="status" className="py-4 text-center text-sm text-slate-500">
      {label}
    </p>
  );
}
