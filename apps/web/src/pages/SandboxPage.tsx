import { useState } from "react";
import type { KeyboardEvent } from "react";
import { Play, SquareTerminal } from "lucide-react";
import { api } from "../lib/api";
import type { SandboxResult } from "../lib/types";
import { PageHeader, Button, Spinner, cx } from "../components/ui";
import { fmtDuration } from "../lib/format";

const SAMPLE = `# Runs inside the locked-down agentos-sandbox container:
#   --network none, 0.5 CPU, 256 MB, 8s timeout.
# Try importing nothing sensitive — there is no network at all.

def fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

print("fib(100) =", fib(100))
print("sum 1..1000  =", sum(range(1, 1001)))

# raise SystemExit(7)   # uncomment to see non-zero exit codes
`;

export default function SandboxPage() {
  const [code, setCode] = useState(SAMPLE);
  const [timeoutS, setTimeoutS] = useState(10);
  const [result, setResult] = useState<SandboxResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(await api.sandboxRun(code, timeoutS));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setRunning(false);
    }
  };

  const canRun = !running && code.trim().length > 0;

  const onEditorKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (canRun) void run();
    }
  };

  return (
    <div>
      <PageHeader
        title="Sandbox"
        desc="Execute untrusted Python in an isolated Docker container — no network, capped CPU/memory, and a hard timeout. The same executor the python.execute tool uses at runtime."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* editor */}
        <div className="overflow-hidden rounded-lg border border-edge bg-panel/70">
          <div className="flex items-center justify-between gap-3 border-b border-edge/70 bg-panel px-3.5 py-2">
            <div className="flex min-w-0 items-center gap-2">
              <SquareTerminal aria-hidden className="h-4 w-4 shrink-0 text-faint" />
              <span className="truncate font-mono text-xs font-medium text-fg">sandbox.py</span>
              <span className="hidden truncate text-[11px] text-faint xl:inline">
                network none · 0.5 CPU · 256 MB
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-2.5">
              <label className="flex items-center gap-1.5 text-xs text-sub">
                <span>timeout</span>
                <input
                  type="number"
                  value={timeoutS}
                  min={1}
                  max={30}
                  onChange={(e) => setTimeoutS(Number(e.target.value) || 10)}
                  aria-label="timeout in seconds"
                  className="h-7 w-14 rounded-md border border-edgehi bg-canvas/60 px-1 text-center font-mono text-xs text-fg focus:border-brand focus:outline-none"
                />
                <span aria-hidden>s</span>
              </label>
              <Button kind="success" size="sm" disabled={!canRun} onClick={() => void run()}>
                {running ? <Spinner /> : <Play aria-hidden className="h-3.5 w-3.5" />}
                {running ? "Running…" : "Run"}
              </Button>
            </div>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={onEditorKeyDown}
            spellCheck={false}
            aria-label="Python code"
            className="h-[520px] w-full resize-none bg-canvas/40 p-4 font-mono text-[13px] leading-relaxed text-fg caret-[#7A8B5E] selection:bg-olive/25"
          />
          <div className="border-t border-edge/70 bg-canvas/40 px-3.5 py-1.5 text-[10px] text-faint">
            Ctrl/⌘ + Enter to run
          </div>
        </div>

        {/* output */}
        <div className="flex flex-col overflow-hidden rounded-lg border border-edge bg-panel/70">
          <div className="flex items-center justify-between border-b border-edge/70 px-3.5 py-2">
            <span className="text-xs font-medium text-sub">Output</span>
            {result && (
              <span className="flex items-center gap-3 font-mono text-[11px]">
                <span
                  className={cx(
                    "font-semibold",
                    result.exit_code === 0 ? "text-olivehi" : "text-rust",
                  )}
                >
                  exit {result.exit_code} · {result.status}
                </span>
                <span className="text-faint">{fmtDuration(result.duration_ms)}</span>
              </span>
            )}
          </div>
          <div className="flex-1 overflow-auto bg-canvas/40 p-4">
            {error && (
              <div role="alert" className="rounded-md border border-rust/35 bg-rust/10 px-3 py-2 text-sm text-rust">
                <span className="font-medium">Sandbox unavailable.</span> {error}
                <p className="mt-1 text-xs text-rust/75">
                  The Studio demo needs the <code className="font-mono">agentos-sandbox</code> Docker
                  image. See README → Docker sandbox for how to build it.
                </p>
              </div>
            )}
            {!error && !result && (
              <div className="text-sm text-faint">Press Run to execute the code.</div>
            )}
            {result?.stdout && (
              <pre className="whitespace-pre-wrap font-mono text-[13px] leading-relaxed text-fg">
                {result.stdout}
              </pre>
            )}
            {result?.stderr && (
              <pre className="mt-2 whitespace-pre-wrap font-mono text-xs leading-relaxed text-rust">
                {result.stderr}
              </pre>
            )}
            {result && !result.stdout && !result.stderr && (
              <div className="text-sm text-faint">No output.</div>
            )}
            {result && result.artifacts.length > 0 && (
              <div className="mt-3 rounded-md border border-olive/35 bg-olive/10 px-3 py-2 text-xs text-olivehi">
                artifacts: {result.artifacts.join(", ")}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
