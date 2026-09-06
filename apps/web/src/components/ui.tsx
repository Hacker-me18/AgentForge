import type { ReactNode } from "react";
import type { ApprovalStatusType, PolicyAction, RunStatus } from "../lib/types";

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

const STATUS_TONE: Record<RunStatus, string> = {
  pending: "bg-gray-500/15 text-gray-300 ring-gray-500/30",
  running: "bg-sky-500/15 text-sky-300 ring-sky-500/30",
  waiting_approval: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  completed: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  failed: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
  cancelled: "bg-gray-500/15 text-gray-400 ring-gray-500/30",
  budget_exceeded: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ring-1",
        STATUS_TONE[status] ?? STATUS_TONE.pending,
      )}
    >
      {status.replace("_", " ")}
    </span>
  );
}

const APPROVAL_TONE: Record<ApprovalStatusType, string> = {
  pending: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
  approved: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  rejected: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
};

export function ApprovalBadge({ status }: { status: ApprovalStatusType }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium capitalize ring-1",
        APPROVAL_TONE[status],
      )}
    >
      {status}
    </span>
  );
}

const POLICY_TONE: Record<PolicyAction, string> = {
  allow: "bg-emerald-500/15 text-emerald-300 ring-emerald-500/30",
  deny: "bg-rose-500/15 text-rose-300 ring-rose-500/30",
  require_approval: "bg-amber-500/15 text-amber-300 ring-amber-500/30",
};

export function PolicyBadge({ action }: { action: PolicyAction }) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1",
        POLICY_TONE[action],
      )}
    >
      {action === "require_approval" ? "requires approval" : action}
    </span>
  );
}

export function Card({
  title,
  subtitle,
  right,
  children,
  className,
  pad = true,
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  pad?: boolean;
}) {
  return (
    <section
      className={cx(
        "rounded-xl border border-gray-800 bg-gray-900/60 shadow-sm",
        className,
      )}
    >
      {(title || right) && (
        <header className="flex items-start justify-between gap-3 border-b border-gray-800/70 px-4 py-3">
          <div>
            {title && (
              <h3 className="text-sm font-semibold tracking-tight text-gray-100">{title}</h3>
            )}
            {subtitle && <p className="mt-0.5 text-xs text-gray-500">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className={pad ? "p-4" : ""}>{children}</div>
    </section>
  );
}

export function Stat({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: "emerald" | "sky" | "violet" | "amber" | "rose" | "gray";
}) {
  const dot = {
    emerald: "text-emerald-400",
    sky: "text-sky-400",
    violet: "text-violet-400",
    amber: "text-amber-400",
    rose: "text-rose-400",
    gray: "text-gray-400",
  }[accent ?? "gray"];
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900/60 px-4 py-3.5">
      <div className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-gray-500">
        <span className={cx("h-1.5 w-1.5 rounded-full", dot)} />
        {label}
      </div>
      <div className="mt-1 text-2xl font-semibold tracking-tight text-gray-50">{value}</div>
      {sub && <div className="mt-0.5 text-xs text-gray-500">{sub}</div>}
    </div>
  );
}

export function PageHeader({
  title,
  desc,
  actions,
}: {
  title: string;
  desc?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-50">{title}</h1>
        {desc && <p className="mt-1 max-w-2xl text-sm text-gray-400">{desc}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-10 text-sm text-gray-500">
      <Spinner />
      {label}
    </div>
  );
}

export function Spinner() {
  return (
    <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-gray-600 border-t-transparent" />
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 px-4 py-3 text-sm text-rose-300">
      <span className="font-medium">Request failed:</span> {message}
      {onRetry && (
        <button onClick={onRetry} className="ml-3 underline underline-offset-2 hover:text-rose-200">
          retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="py-12 text-center">
      <div className="text-sm font-medium text-gray-400">{title}</div>
      {hint && <div className="mt-1 text-xs text-gray-600">{hint}</div>}
    </div>
  );
}

export function KV({ rows }: { rows: Array<[string, ReactNode]> }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-gray-800/50 py-1 text-xs">
          <dt className="text-gray-500">{k}</dt>
          <dd className="font-mono text-right text-gray-200">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Button({
  children,
  onClick,
  kind = "primary",
  disabled,
  type = "button",
  className,
}: {
  children: ReactNode;
  onClick?: () => void;
  kind?: "primary" | "ghost" | "danger" | "success";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
}) {
  const styles = {
    primary:
      "bg-gray-200 text-gray-900 hover:bg-white disabled:opacity-40",
    ghost:
      "border border-gray-700 bg-transparent text-gray-300 hover:bg-gray-800 disabled:opacity-40",
    danger: "bg-rose-600/90 text-white hover:bg-rose-500 disabled:opacity-40",
    success: "bg-emerald-600/90 text-white hover:bg-emerald-500 disabled:opacity-40",
  }[kind];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={cx(
        "inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors",
        styles,
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Dot({ tone }: { tone: string }) {
  return <span className={cx("inline-block h-1.5 w-1.5 rounded-full", tone)} />;
}
