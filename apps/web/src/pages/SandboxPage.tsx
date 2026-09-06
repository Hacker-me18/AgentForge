import { useState } from "react";
import { api } from "../lib/api";
import type { SandboxResult } from "../lib/types";
import { PageHeader, Button, cx } from "../components/ui";
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

  return (
    <div>
      <PageHeader
        title="Sandbox"
        desc="Execute untrusted Python in an isolated Docker container — no network, capped CPU/memory, and a hard timeout. The same executor the python.execute tool uses at runtime."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="overflow-hidden rounded-xl border border-gray-800">
          <div className="flex items-center justify-between border-b border-gray-800 bg-gray-900 px-4 py-2">
            <div className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-500/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/70" />
              <span className="ml-2 text-xs font-medium text-gray-400">agentos-sandbox / python</span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={timeoutS}
                min={1}
                max={30}
                onChange={(e) => setTimeoutS(Number(e.target.value) || 10)}
                className="w-16 rounded-md border border-gray-700 bg-gray-950 px-2 py-1 text-center font-mono text-xs text-gray-300 focus:border-sky-500 focus:outline-none"
                title="timeout seconds"
              />
              <span className="text-xs text-gray-600">s</span>
              <Button onClick={() => void run()} disabled={running || !code.trim()} kind="success">
                {running ? "Running…" : "Run ▶"}
              </Button>
            </div>
          </div>
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            spellCheck={false}
            className="h-[520px] w-full resize-none bg-gray-950 p-4 font-mono text-[12.5px] leading-relaxed text-emerald-200/90 focus:outline-none"
            style={{ caretColor: "#fbbf24" }}
          />
        </div>

        <div className="flex flex-col overflow-hidden rounded-xl border border-gray-800">
          <div className="border-b border-gray-800 bg-gray-900 px-4 py-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-gray-400">Output</span>
              {result && (
                <span className="flex items-center gap-3 font-mono text-[11px]">
                  <span
                    className={cx(
                      "font-semibold",
                      result.exit_code === 0 ? "text-emerald-400" : "text-rose-400",
                    )}
                  >
                    exit {result.exit_code} · {result.status}
                  </span>
                  <span className="text-gray-500">{fmtDuration(result.duration_ms)}</span>
                </span>
              )}
            </div>
          </div>
          <div className="flex-1 overflow-auto bg-gray-950 p-4">
            {error && (
              <div className="rounded-md border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-sm text-rose-300">
                <span className="font-medium">Sandbox unavailable.</span> {error}
                <p className="mt-1 text-xs text-rose-300/70">
                  The Studio demo needs the <code className="font-mono">agentos-sandbox</code> Docker
                  image. See README → Docker sandbox for how to build it.
                </p>
              </div>
            )}
            {!error && !result && (
              <div className="text-sm text-gray-600">Press Run to execute the code.</div>
            )}
            {result?.stdout && (
              <pre className="whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed text-gray-200">
                {result.stdout}
              </pre>
            )}
            {result?.stderr && (
              <pre className="mt-2 whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-rose-300">
                {result.stderr}
              </pre>
            )}
            {result && !result.stdout && !result.stderr && (
              <div className="text-sm text-gray-600">No output.</div>
            )}
            {result && result.artifacts.length > 0 && (
              <div className="mt-3 rounded-md border border-sky-500/20 bg-sky-500/5 px-3 py-2 text-xs text-sky-300">
                artifacts: {result.artifacts.join(", ")}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
