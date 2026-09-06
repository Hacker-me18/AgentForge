import type { CSSProperties, ReactNode } from "react";
import { Inbox, Loader2, TriangleAlert } from "lucide-react";
import type { ApprovalStatusType, PolicyAction, RunStatus } from "../lib/types";

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/* ---------------------------------------------------------------------------
 * Warm-organic tokens
 * Neutrals are paper / sand / clay (never cool grey). The only accents are
 * terracotta (`brand`) for action + attention and olive for calm / tags.
 * ------------------------------------------------------------------------- */

/* Shared control styling. Warm clay borders, sand wells, no glass. */
export const inputCls =
  "h-8 rounded-lg border border-clay/80 bg-sand/30 px-2.5 text-[13px] text-ink placeholder:text-[#9A8C78] hover:border-[#C2A88A] focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand/25";
export const tagCls =
  "inline-flex items-center gap-1 rounded-md bg-sand/60 px-1.5 py-0.5 font-mono text-[11px] text-[#6E624F] ring-1 ring-inset ring-clay/60";

export type Tone = "neutral" | "olive" | "terra" | "ochre" | "rust" | "brand";

const TONES: Record<Tone, { bg: string; line: string; text: string; dot: string }> = {
  neutral: { bg: "bg-sand/60", line: "border-clay/70", text: "text-ink/70", dot: "bg-[#AB9C86]" },
  olive: { bg: "bg-olive/15", line: "border-olive/45", text: "text-olivehi", dot: "bg-olive" },
  terra: { bg: "bg-brand/14", line: "border-brand/45", text: "text-brandhi", dot: "bg-brand" },
  ochre: { bg: "bg-[#B0813C]/14", line: "border-[#B0813C]/45", text: "text-[#7C5A22]", dot: "bg-[#B0813C]" },
  rust: { bg: "bg-rust/14", line: "border-rust/45", text: "text-rust", dot: "bg-rust" },
  brand: { bg: "bg-brand", line: "border-brand", text: "text-white", dot: "bg-white/85" },
};

/** Rounded chip with a leading dot — status / approval / policy markers. */
export function Pill({ tone = "neutral", label }: { tone?: Tone; label: string }) {
  const t = TONES[tone];
  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border px-2 py-[3px] text-[11px] font-medium capitalize",
        t.bg,
        t.line,
        t.text,
      )}
    >
      <span aria-hidden className={cx("h-1.5 w-1.5 rounded-full", t.dot)} />
      {label}
    </span>
  );
}

/** Generic coloured chip — same visual language as the status badges. */
export function Badge({ tone = "neutral", label }: { tone?: Tone; label: string }) {
  return <Pill tone={tone} label={label} />;
}

/** Compact square tinted tag (feed kinds, metadata) — no dot, ring only. */
export function Chip({ tone = "neutral", label }: { tone?: Tone; label: string }) {
  const t = TONES[tone];
  return (
    <span
      className={cx(
        "inline-flex items-center whitespace-nowrap rounded-md px-1.5 py-px font-mono text-[11px] font-medium ring-1 ring-inset",
        t.bg,
        t.text,
        t.line.replace("border-", "ring-"),
      )}
    >
      {label}
    </span>
  );
}

const STATUS_TONE: Record<RunStatus, Tone> = {
  pending: "neutral",
  running: "ochre",
  waiting_approval: "terra",
  completed: "olive",
  failed: "rust",
  cancelled: "neutral",
  budget_exceeded: "rust",
};

export function StatusBadge({ status }: { status: RunStatus }) {
  return <Pill tone={STATUS_TONE[status]} label={status.replace("_", " ")} />;
}

const APPROVAL_TONE: Record<ApprovalStatusType, Tone> = {
  pending: "terra",
  approved: "olive",
  rejected: "rust",
};

export function ApprovalBadge({ status }: { status: ApprovalStatusType }) {
  return <Pill tone={APPROVAL_TONE[status]} label={status} />;
}

const POLICY_TONE: Record<PolicyAction, Tone> = {
  allow: "olive",
  deny: "rust",
  require_approval: "terra",
};

export function PolicyBadge({ action }: { action: PolicyAction }) {
  return (
    <Pill
      tone={POLICY_TONE[action]}
      label={action === "require_approval" ? "requires approval" : action}
    />
  );
}

/* ---------------------------------------------------------------------------
 * Page / Card / Stat primitives
 * ------------------------------------------------------------------------- */

/** Panel title: small serif, weight 500, sits on a hairline header. */
function panelTitle() {
  return "font-serif text-[15px] font-medium tracking-tight text-ink";
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
    <div className="mb-7 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="font-serif text-[26px] font-medium leading-tight tracking-tight text-ink">
          {title}
        </h1>
        {desc && <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-[#7C7160]">{desc}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function Card({
  title,
  subtitle,
  right,
  children,
  className,
  pad = true,
  titleTag = "h2",
}: {
  title?: ReactNode;
  subtitle?: ReactNode;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
  pad?: boolean;
  titleTag?: "h2" | "h3";
}) {
  const TitleTag = titleTag;
  return (
    <section
      className={cx(
        "overflow-hidden rounded-lg border border-edge bg-panel shadow-card",
        className,
      )}
    >
      {(title || right) && (
        <header className="flex items-start justify-between gap-3 border-b border-edge/80 bg-canvas/50 px-4 py-2.5">
          <div className="min-w-0">
            {title && <TitleTag className={cx(panelTitle(), "truncate")}>{title}</TitleTag>}
            {subtitle && <p className="mt-0.5 text-xs text-[#8A7C69]">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      <div className={pad ? "p-4" : ""}>{children}</div>
    </section>
  );
}

/** Open value + caption — no chrome, so it works in a row, band or grid. */
export function Stat({
  label,
  value,
  sub,
  valueClass,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  valueClass?: string;
}) {
  return (
    <div className="min-w-0">
      <div className="text-xs font-medium text-[#8A7C69]">{label}</div>
      <div
        className={cx(
          "mt-0.5 text-2xl font-semibold tracking-tight tabular-nums",
          valueClass ?? "text-ink",
        )}
      >
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-[#8A7C69]">{sub}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Loading / skeleton / empty / error
 * ------------------------------------------------------------------------- */

export function Spinner() {
  return <Loader2 aria-hidden className="h-3.5 w-3.5 animate-spin text-brand" />;
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-8 text-sm text-[#8A7C69]">
      <Spinner />
      {label}
    </div>
  );
}

export function Skeleton({ className, style }: { className?: string; style?: CSSProperties }) {
  return <div aria-hidden style={style} className={cx("animate-pulse rounded-md bg-raised", className)} />;
}

export function TableSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div
      role="status"
      aria-label="Loading data"
      className="overflow-hidden rounded-lg border border-edge bg-panel shadow-card"
    >
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className={cx("flex items-center gap-3 px-4 py-3", i > 0 && "border-t border-edge/70")}
        >
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-44" />
          <div className="ml-auto flex gap-2">
            <Skeleton className="h-3 w-12" />
            <Skeleton className="h-3 w-12" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div
      role="alert"
      className="flex items-start gap-2.5 rounded-lg border border-rust/40 bg-rust/10 px-3.5 py-3 text-sm text-rust"
    >
      <TriangleAlert aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-rust" />
      <div className="min-w-0 break-words">
        <span className="font-medium">Request failed:</span> {message}
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="ml-auto shrink-0 rounded text-xs font-medium underline underline-offset-2 hover:text-[#7E2E18]"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({
  title,
  hint,
  icon = true,
}: {
  title: string;
  hint?: string;
  icon?: boolean;
}) {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-10 text-center">
      {icon && <Inbox aria-hidden className="mb-2 h-5 w-5 text-clay" strokeWidth={1.5} />}
      <div className="text-sm font-medium text-ink">{title}</div>
      {hint && <div className="mt-1 max-w-sm text-xs leading-relaxed text-[#8A7C69]">{hint}</div>}
    </div>
  );
}

/** Inline banner for transient feedback (save success, rerun error). */
export function Notice({ tone, children }: { tone: "success" | "error"; children: ReactNode }) {
  const styles =
    tone === "success"
      ? "border-olive/45 bg-olive/12 text-olivehi"
      : "border-rust/40 bg-rust/10 text-rust";
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cx("rounded-lg border px-3.5 py-2 text-[13px]", styles)}
    >
      {children}
    </div>
  );
}

/* ---------------------------------------------------------------------------
 * Misc
 * ------------------------------------------------------------------------- */

export function KV({ rows }: { rows: Array<[string, ReactNode]> }) {
  return (
    <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 sm:grid-cols-2">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3 border-b border-edge/80 py-1.5 text-xs">
          <dt className="text-[#8A7C69]">{k}</dt>
          <dd className="font-mono text-right text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

export function Button({
  children,
  onClick,
  kind = "primary",
  size = "md",
  disabled,
  type = "button",
  className,
  title,
}: {
  children: ReactNode;
  onClick?: () => void;
  kind?: "primary" | "ghost" | "danger" | "success";
  size?: "sm" | "md";
  disabled?: boolean;
  type?: "button" | "submit";
  className?: string;
  title?: string;
}) {
  const sizes = {
    sm: "h-7 gap-1.5 rounded-lg px-2.5 text-xs",
    md: "h-8 gap-1.5 rounded-lg px-3 text-[13px]",
  }[size];
  const kinds = {
    primary: "bg-brand text-white shadow-card hover:bg-brandhi",
    ghost: "border border-clay/80 bg-transparent text-ink hover:bg-sand/50",
    danger: "bg-rust text-white shadow-card hover:opacity-90",
    success: "bg-olive text-white shadow-card hover:bg-olivehi",
  }[kind];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={cx(
        "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 active:scale-[0.98] disabled:opacity-45",
        sizes,
        kinds,
        className,
      )}
    >
      {children}
    </button>
  );
}

export function Tag({ children, className }: { children: ReactNode; className?: string }) {
  return <span className={cx(tagCls, className)}>{children}</span>;
}

export function Dot({ tone, pulse }: { tone: string; pulse?: boolean }) {
  return (
    <span
      aria-hidden
      className={cx("inline-block h-1.5 w-1.5 shrink-0 rounded-full", tone, pulse && "animate-pulse")}
    />
  );
}
