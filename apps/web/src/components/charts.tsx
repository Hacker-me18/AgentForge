// Dependency-free bar charts: horizontal usage bars + a vertical day histogram.
// The single series colour is the pine brand accent; text never depends on it.

import { cx } from "./ui";
import type { TimelinePoint } from "../lib/types";

/** One horizontal bar row. Numeric label + value are real text; the bar is
 *  decorative and hidden from assistive tech. */
export function HBar({
  label,
  value,
  max,
  format = (v) => String(v),
  barClass = "bg-olive",
}: {
  label: string;
  value: number;
  max: number;
  format?: (v: number) => string;
  barClass?: string;
}) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return (
    <div className="flex items-center gap-3 py-[4px]">
      <div className="w-36 shrink-0 truncate text-right font-mono text-xs text-sub">{label}</div>
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-raised">
        <div aria-hidden className={cx("h-full rounded-full", barClass)} style={{ width: `${pct}%` }} />
      </div>
      <div className="w-16 shrink-0 text-right font-mono text-xs text-fg tabular-nums">{format(value)}</div>
    </div>
  );
}

/** Vertical bars for the runs-per-day timeline. Labels are DD Mon. */
export function TimelineBars({
  points,
  color = "bg-olive",
}: {
  points: TimelinePoint[];
  color?: string;
}) {
  const max = Math.max(1, ...points.map((p) => p.runs));
  return (
    <div className="flex h-40 items-end gap-2">
      {points.length === 0 && (
        <div className="flex h-full w-full items-center justify-center text-xs text-sub">
          No runs recorded yet
        </div>
      )}
      {[...points].reverse().map((p) => {
        const [, mon, day] = p.day.split("-");
        const months = [
          "",
          "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ];
        const label = `${months[Number(mon)]} ${Number(day)}`;
        const h = Math.max(4, Math.round((p.runs / max) * 100));
        return (
          <div key={p.day} className="group flex flex-1 flex-col items-center justify-end gap-1.5">
            <span className="text-[10px] font-medium tabular-nums text-sub">{p.runs}</span>
            <div
              aria-hidden
              title={`${label} — ${p.runs} runs`}
              className={cx(
                "w-full max-w-[26px] rounded-md rounded-b-sm transition-opacity",
                color,
                "group-hover:opacity-80",
              )}
              style={{ height: `${h}px` }}
            />
            <span aria-hidden className="truncate text-[10px] text-faint">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Two-sided comparison row (score vs ideal / control vs treatment). Both arms
 *  draw neutral by default; colour is only ever semantic when passed in. */
export function CompareBar({
  dimension,
  a,
  b,
  aLabel,
  bLabel,
  format = (v: number) => `${Math.round(v * 100)}%`,
  aClass = "bg-[#CDB79A]",
  bClass = "bg-[#E5D8C5]",
}: {
  dimension: string;
  a: number;
  b: number;
  aLabel: string;
  bLabel: string;
  format?: (v: number) => string;
  aClass?: string;
  bClass?: string;
}) {
  return (
    <div className="py-2">
      <div className="mb-1.5 flex items-center justify-between gap-3">
        <span className="truncate text-xs font-medium text-fg">{dimension}</span>
        <span className="shrink-0 font-mono text-[10px] text-sub">
          {aLabel} <span className="text-fg">{format(a)}</span>
          <span aria-hidden className="mx-1.5 text-faint">·</span>
          {bLabel} <span className="text-fg">{format(b)}</span>
        </span>
      </div>
      <div className="flex items-center gap-1.5">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-raised">
          <div
            aria-hidden
            className={cx("h-full rounded-full", aClass)}
            style={{ width: `${Math.round(Math.max(0, Math.min(1, a)) * 100)}%` }}
          />
        </div>
        <div aria-hidden className="h-3 w-px bg-edgehi" />
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-raised">
          <div
            aria-hidden
            className={cx("h-full rounded-full", bClass)}
            style={{ width: `${Math.round(Math.max(0, Math.min(1, b)) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
