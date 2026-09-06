import { useState } from "react";
import type { RunStatus, Span, Trace } from "../lib/types";
import { fmtDuration, fmtNumber, fmtMoney, fmtTime } from "../lib/format";
import { StatusBadge, cx } from "./ui";

const KIND_STYLE: Record<string, { bar: string; text: string; label: string }> = {
  run: { bar: "bg-gray-200", text: "text-gray-100", label: "run" },
  context: { bar: "bg-gray-500", text: "text-gray-300", label: "ctx" },
  llm: { bar: "bg-violet-400", text: "text-violet-300", label: "llm" },
  tool: { bar: "bg-sky-400", text: "text-sky-300", label: "tool" },
  sandbox: { bar: "bg-amber-400", text: "text-amber-300", label: "sandbox" },
  approval: { bar: "bg-amber-400", text: "text-amber-300", label: "guard" },
  event: { bar: "bg-gray-600", text: "text-gray-400", label: "evt" },
};

function kindStyle(kind: string) {
  return KIND_STYLE[kind] ?? { bar: "bg-gray-600", text: "text-gray-400", label: kind };
}

function SpanRow({ span, depth }: { span: Span; depth: number }) {
  const [open, setOpen] = useState(depth === 0);
  const style = kindStyle(span.kind);
  const hasDetail = Object.keys(span.attrs).length > 0;

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        className={cx(
          "group flex w-full items-center gap-2 rounded-md px-2 py-1 text-left hover:bg-gray-800/60",
          depth > 0 && "ml-3",
        )}
        style={{ paddingLeft: `${10 + depth * 14}px` }}
      >
        <span className={cx("h-3 w-0.5 shrink-0 rounded", style.bar)} />
        {hasDetail && (
          <svg
            viewBox="0 0 16 16"
            className={cx("h-3 w-3 shrink-0 text-gray-500 transition-transform", open && "rotate-90")}
            fill="currentColor"
          >
            <path d="M6 4l6 4-6 4z" />
          </svg>
        )}
        {!hasDetail && <span className="w-3 shrink-0" />}
        <span className={cx("font-mono text-xs", style.text)}>{span.name}</span>
        {span.kind === "tool" && typeof span.attrs["tool"] === "string" && (
          <span className="text-[10px] text-gray-600">{span.attrs["tool"]}</span>
        )}
        <span className="ml-auto font-mono text-[10px] text-gray-500">
          {span.status === "failed" ? (
            <span className="text-rose-400">failed</span>
          ) : (
            fmtDuration(span.duration_ms)
          )}
        </span>
      </button>
      {open && hasDetail && (
        <pre
          className={cx("ml-6 mt-0.5 overflow-x-auto rounded-md bg-gray-950/70 p-2", depth > 0 && "ml-8")}
          style={{ paddingLeft: `${10 + depth * 14 + 14}px` }}
        >
          <code className="whitespace-pre-wrap font-mono text-[10.5px] leading-relaxed text-gray-400">
            {JSON.stringify(span.attrs, null, 2)}
          </code>
        </pre>
      )}
      {span.children.map((child) => (
        <SpanRow key={`${child.kind}-${child.start}`} span={child} depth={depth + 1} />
      ))}
    </div>
  );
}

export function TraceTree({ trace }: { trace: Trace }) {
  const root = trace.root;
  const rawSteps = root.attrs["steps"];
  const steps = typeof rawSteps === "number" ? fmtNumber(rawSteps) : "—";
  const runStatus: RunStatus =
    root.status === "failed"
      ? "failed"
      : root.status === "running" || root.end === null
        ? "running"
        : "completed";
  const answer = root.attrs["answer"];
  const task = root.attrs["task"];
  const agent = root.attrs["agent_id"];

  return (
    <div>
      {/* Run header */}
      <div className="rounded-lg border border-gray-800 bg-gray-900/70 p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-400">Run</span>
            <StatusBadge status={runStatus} />
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[10.5px] text-gray-500">
            <span>
              steps <span className="text-gray-300">{steps}</span>
            </span>
            <span>
              dur <span className="text-gray-300">{fmtDuration(root.duration_ms)}</span>
            </span>
            <span>
              tokens <span className="text-gray-300">{fmtNumber(trace.summary.total_tokens)}</span>
            </span>
            <span>
              cost <span className="text-emerald-400">{fmtMoney(trace.summary.cost)}</span>
            </span>
          </div>
        </div>
        {typeof task === "string" && (
          <div className="mt-2 text-sm text-gray-200">
            <span className="text-gray-600">task:</span> {task}
          </div>
        )}
        {typeof agent === "string" && agent && (
          <div className="mt-0.5 font-mono text-[10.5px] text-gray-600">agent: {agent}</div>
        )}
        {typeof answer === "string" && (
          <div className="mt-2 rounded-md border border-emerald-500/20 bg-emerald-500/5 px-2.5 py-2">
            <div className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">
              final answer
            </div>
            <pre className="mt-1 whitespace-pre-wrap font-sans text-xs leading-relaxed text-gray-100">
              {answer}
            </pre>
          </div>
        )}
        {typeof root.attrs["error"] === "string" && root.attrs["error"] && (
          <div className="mt-2 rounded-md border border-rose-500/20 bg-rose-500/5 px-2.5 py-1.5 text-xs text-rose-300">
            {root.attrs["error"]}
          </div>
        )}
      </div>

      {/* Span tree */}
      <div className="mt-3 space-y-0.5 rounded-lg border border-gray-800 bg-gray-900/40 py-2">
        <div className="flex items-center gap-2 px-3 pb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-600">
          <span>trace</span>
          <span className="ml-auto font-normal normal-case text-gray-600">
            started {fmtTime(root.start)}
          </span>
        </div>
        {root.children.length === 0 && (
          <div className="px-4 py-3 text-xs text-gray-600">No span events recorded for this run.</div>
        )}
        {root.children.map((child) => (
          <SpanRow key={`${child.kind}-${child.start}`} span={child} depth={0} />
        ))}
      </div>
    </div>
  );
}
