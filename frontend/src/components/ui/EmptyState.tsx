import type { ReactNode } from "react";

export function EmptyState({
  icon,
  title,
  body,
  cta,
}: {
  icon: ReactNode;
  title: string;
  body: string;
  cta?: ReactNode;
}) {
  return (
    <div className="mt-8 rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
      <div className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-500">
        {icon}
      </div>
      <h3 className="mt-3 text-base font-semibold text-slate-800">{title}</h3>
      <p className="mx-auto mt-1 max-w-md text-sm text-slate-500">{body}</p>
      {cta && <div className="mt-4 flex justify-center">{cta}</div>}
    </div>
  );
}
