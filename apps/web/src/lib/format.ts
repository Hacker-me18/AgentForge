// Display helpers: numbers, currency, tokens, time.

export function fmtNumber(n: number): string {
  return n.toLocaleString("en-US");
}

/** Compact currency, e.g. $0.000606 → "$0.000606"; trims trailing zeros. */
export function fmtMoney(n: number): string {
  if (n === 0) return "$0";
  const rounded = Number(n.toPrecision(4));
  return `$${rounded}`;
}

export function fmtCost(n: number): string {
  return `$${n.toFixed(6)}`;
}

export function fmtDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${ms.toFixed(ms < 10 ? 1 : 0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/** Unix epoch seconds → "06 Sep 14:21". */
export function fmtTime(sec: number | null | undefined): string {
  if (sec === null || sec === undefined) return "—";
  const d = new Date(sec * 1000);
  const pad = (x: number) => String(x).padStart(2, "0");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${pad(d.getDate())} ${months[d.getMonth()]} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function fmtDateTime(sec: number | null | undefined): string {
  if (sec === null || sec === undefined) return "—";
  const d = new Date(sec * 1000);
  return d.toLocaleString();
}

/** Short human age: "just now", "42s ago", "5m ago", "2h ago". */
export function fmtAgo(sec: number | null | undefined): string {
  if (sec === null || sec === undefined) return "—";
  const delta = Math.max(0, Date.now() / 1000 - sec);
  if (delta < 5) return "just now";
  if (delta < 60) return `${Math.floor(delta)}s ago`;
  if (delta < 3600) return `${Math.floor(delta / 60)}m ago`;
  if (delta < 86400) return `${Math.floor(delta / 3600)}h ago`;
  return `${Math.floor(delta / 86400)}d ago`;
}

export function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

export function splitLines(s: string): string[] {
  return s.split(/\r?\n/);
}
