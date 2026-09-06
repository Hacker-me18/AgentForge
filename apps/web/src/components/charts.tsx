// Dependency-free bar charts: horizontal usage bars + a vertical day histogram.

import { cx } from "./ui";
import type { TimelinePoint } from "../lib/types";

export function HBar({
  label,
  value,
  max,
  format = (v) => String(v),
  barClass = "bg-sky-500",
}: {
  label: string;
  value: number;
  max: number;
  format?: (v: number) => string;
  barClass?: string;
}) {
  const pct = max > 0 ? Math.max(2, Math.round((value / max) * 100)) : 0;
  return (
    <div className="flex items-center gap-3 py-[3px]">
      <div className="w-40 truncate text-right font-mono text-xs text-gray-400">{label}</div>
      <div className="h-4 flex-1 overflow-hidden rounded bg-gray-800/70">
        <div
          className={cx("h-full rounded transition-all", barClass)}
          style={{ width: `${pct}%`, opacity: 0.35 + 0.65 * (value / max) }}
        />
      </div>
      <div className="w-16 text-right font-mono text-xs text-gray-200">{format(value)}</div>
    </div>
  );
}

/** Vertical bars for the runs-per-day timeline. Labels are DD Mon. */
export function TimelineBars({ points, color = "bg-sky-400" }: { points: TimelinePoint[]; color?: string }) {
  const max = Math.max(1, ...points.map((p) => p.runs));
  return (
    <div className="flex h-36 items-end gap-1.5">
      {points.length === 0 && (
        <div className="flex h-full w-full items-center justify-center text-xs text-gray-600">
          No runs recorded yet
        </div>
      )}
      {[...points].reverse().map((p) => {
        const [, mon, day] = p.day.split("-");
        const months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const label = `${months[Number(mon)]} ${Number(day)}`;
        const h = Math.max(4, Math.round((p.runs / max) * 100));
        return (
          <div key={p.day} className="group flex flex-1 flex-col justify-end items-center gap-1">
            <span className="text-[10px] font-semibold text-gray-400">{p.runs}</span>
            <div
              title={`${label} — ${p.runs} runs`}
              className={cx("w-full max-w-[26px] rounded-t-md transition-colors", color)}
              style={{ height: `${h}px` }}
            />
            <span className="truncate text-[9px] text-gray-600">{label}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Comparison row for evaluation dimensions (control vs treatment / target). */
export function CompareBar({
  dimension,
  a,
  b,
  aLabel,
  bLabel,
  format = (v: number) => `${Math.round(v * 100)}%`,
}: {
  dimension: string;
  a: number;
  b: number;
  aLabel: string;
  bLabel: string;
  format?: (v: number) => string;
}) {
  return (
    <div className="py-2">
      <div className="mb-1 flex items-center justify-between">
        <span className="text-xs font-medium text-gray-300">{dimension}</span>
        <span className="font-mono text-[10px] text-gray-500">
          {aLabel} <span className="text-gray-300">{format(a)}</span>
          &nbsp;·&nbsp; {bLabel} <span className="text-gray-300">{format(b)}</span>
        </span>
      </div>
      <div className="flex items-center gap-1">
        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-gray-800">
          <div
            className="h-full rounded-full bg-emerald-500/80"
            style={{ width: `${Math.round(Math.max(0, a) * 100)}%` }}
          />
        </div>
        <div className="mx-1 h-2.5 w-px bg-gray-700" />
        <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-gray-800">
          <div
            className="h-full rounded-full bg-sky-500/80"
            style={{ width: `${Math.round(Math.max(0, b) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
}
