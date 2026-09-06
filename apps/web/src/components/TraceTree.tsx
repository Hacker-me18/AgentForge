import { useState } from "react";
import { ChevronRight } from "lucide-react";
import type { RunStatus, Span, Trace } from "../lib/types";
import { fmtDuration, fmtNumber, fmtMoney, fmtTime } from "../lib/format";
import { StatusBadge, cx } from "./ui";

/* Warm gutter bars — no cool greys or neon hues; runs/context/events sit in
 * sand neutrals while model, tool and guardrail work keep their warm hues. */
const KIND_STYLE: Record<string, { bar: string; label: string }> = {
  run: { bar: "bg-[#9C8E72]", label: "run" },
  context: { bar: "bg-[#BBAE92]", label: "ctx" },
  llm: { bar: "bg-[#B0813C]", label: "llm" },
  tool: { bar: "bg-olive", label: "tool" },
  sandbox: { bar: "bg-brand", label: "box" },
  approval: { bar: "bg-[#B75A35]", label: "guard" },
  event: { bar: "bg-[#C9B79B]", label: "evt" },
};

function kindStyle(kind: string) {
  return KIND_STYLE[kind] ?? { bar: "bg-[#C9B79B]", label: kind };
}

function SpanRow({ span, depth }: { span: Span; depth: number }) {
  const [open, setOpen] = useState(depth === 0);
  const style = kindStyle(span.kind);
  const hasDetail = Object.keys(span.attrs).length > 0;
  const indent = { paddingLeft: `${10 + depth * 14}px` };

  const gutter = (
    <>
      <span aria-hidden className={cx("h-3 w-[3px] shrink-0 rounded-full", style.bar)} />
      <span className="w-8 shrink-0 text-right font-mono text-[9px] text-[#A0927C]">
        {style.label}
      </span>
    </>
  );

  if (!hasDetail) {
    return (
      <div className="flex w-full items-center gap-2 rounded-md px-2 py-1 text-left" style={indent}>
        {gutter}
        <span className="truncate font-mono text-xs text-fg">{span.name}</span>
        {span.kind === "tool" && typeof span.attrs["tool"] === "string" && (
          <span className="truncate text-[11px] text-faint">{span.attrs["tool"]}</span>
        )}
        <span className="ml-auto shrink-0 font-mono text-[10px] text-faint">
          {span.status === "failed" ? (
            <span className="text-rust">failed</span>
          ) : (
            fmtDuration(span.duration_ms)
          )}
        </span>
      </div>
    );
  }

  return (
    <div>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`${style.label} ${span.name}`}
        className="group flex w-full items-center gap-2 rounded-md px-2 py-1 text-left hover:bg-raised/70"
        style={indent}
      >
        {gutter}
        <ChevronRight
          aria-hidden
          className={cx("h-3 w-3 shrink-0 text-faint transition-transform", open && "rotate-90")}
          strokeWidth={2.5}
        />
        <span className="truncate font-mono text-xs text-fg">{span.name}</span>
        {span.kind === "tool" && typeof span.attrs["tool"] === "string" && (
          <span className="truncate text-[11px] text-faint">{span.attrs["tool"]}</span>
        )}
        <span className="ml-auto shrink-0 font-mono text-[10px] text-faint">
          {span.status === "failed" ? (
            <span className="text-rust">failed</span>
          ) : (
            fmtDuration(span.duration_ms)
          )}
        </span>
      </button>
      {open && (
        <pre
          className={cx("ml-6 mt-0.5 overflow-x-auto rounded-md bg-canvas/70 p-2", depth > 0 && "ml-8")}
          style={{ paddingLeft: `${10 + depth * 14 + 22}px` }}
        >
          <code className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-sub">
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
      <div className="rounded-lg border border-edge bg-panel/80 p-3">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2.5">
            <span className="font-serif text-[13px] font-medium tracking-tight text-ink">Run</span>
            <StatusBadge status={runStatus} />
          </div>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 font-mono text-[11px] text-faint">
            <span>
              steps <span className="text-fg">{steps}</span>
            </span>
            <span>
              dur <span className="text-fg">{fmtDuration(root.duration_ms)}</span>
            </span>
            <span>
              tokens <span className="text-fg">{fmtNumber(trace.summary.total_tokens)}</span>
            </span>
            <span>
              cost <span className="text-fg">{fmtMoney(trace.summary.cost)}</span>
            </span>
          </div>
        </div>
        {typeof task === "string" && (
          <div className="mt-2 text-sm text-fg">
            <span className="text-faint">task:</span> {task}
          </div>
        )}
        {typeof agent === "string" && agent && (
          <div className="mt-0.5 font-mono text-[11px] text-faint">agent: {agent}</div>
        )}
        {typeof answer === "string" && (
          <div className="mt-2 rounded-md border border-olive/35 bg-olive/10 px-2.5 py-2">
            <div className="text-[11px] font-semibold text-olivehi">final answer</div>
            <pre className="mt-1 whitespace-pre-wrap font-sans text-xs leading-relaxed text-fg">
              {answer}
            </pre>
          </div>
        )}
        {typeof root.attrs["error"] === "string" && root.attrs["error"] && (
          <div className="mt-2 rounded-md border border-rust/35 bg-rust/10 px-2.5 py-1.5 text-xs text-rust">
            {root.attrs["error"]}
          </div>
        )}
      </div>

      {/* Span tree */}
      <div className="mt-3 space-y-px rounded-lg border border-edge bg-panel/40 py-1.5">
        <div className="flex items-center gap-2 px-3 pb-1 text-[11px] font-medium text-[#8A7C69]">
          <span>trace</span>
          <span className="ml-auto font-normal text-[#A0927C]">started {fmtTime(root.start)}</span>
        </div>
        {root.children.length === 0 && (
          <div className="px-4 py-3 text-xs text-faint">No span events recorded for this run.</div>
        )}
        {root.children.map((child) => (
          <SpanRow key={`${child.kind}-${child.start}`} span={child} depth={0} />
        ))}
      </div>
    </div>
  );
}
