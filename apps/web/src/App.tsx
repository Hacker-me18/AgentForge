import { NavLink, Route, Routes } from "react-router-dom";
import OverviewPage from "./pages/OverviewPage";
import AgentsPage from "./pages/AgentsPage";
import RunsPage from "./pages/RunsPage";
import TracesPage from "./pages/TracesPage";
import ToolsPage from "./pages/ToolsPage";
import SandboxPage from "./pages/SandboxPage";
import PoliciesPage from "./pages/PoliciesPage";
import EvaluationsPage from "./pages/EvaluationsPage";
import ExperimentsPage from "./pages/ExperimentsPage";
import SettingsPage from "./pages/SettingsPage";
import { cx } from "./components/ui";

const NAV_ITEMS: Array<{ path: string; label: string; end?: boolean }> = [
  { path: "/", label: "Overview", end: true },
  { path: "/agents", label: "Agents" },
  { path: "/runs", label: "Runs" },
  { path: "/traces", label: "Traces" },
  { path: "/tools", label: "Tools" },
  { path: "/sandbox", label: "Sandbox" },
  { path: "/policies", label: "Policies" },
  { path: "/evaluations", label: "Evaluations" },
  { path: "/experiments", label: "Experiments" },
  { path: "/settings", label: "Settings" },
];

function Wordmark() {
  return (
    <NavLink to="/" end className="group flex shrink-0 items-center gap-2.5" aria-label="AgentForge Studio home">
      <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand font-serif text-[18px] font-semibold leading-none text-[#FBF6EE] shadow-card transition-colors group-hover:bg-brandhi">
        a
      </span>
      <span className="flex flex-col leading-none">
        <span className="font-serif text-[16px] font-semibold tracking-tight text-ink">AgentForge</span>
        <span className="mt-0.5 font-sans text-[10px] font-medium tracking-[0.14em] text-[#8A7C69]">
          Studio
        </span>
      </span>
    </NavLink>
  );
}

export default function App() {
  return (
    <div className="min-h-screen bg-canvas font-sans text-fg">
      <header className="sticky top-0 z-30 border-b border-edge bg-panel">
        <div className="mx-auto flex h-14 w-full max-w-[1200px] items-center gap-4 px-5 lg:px-6">
          <Wordmark />
          <nav className="flex min-w-0 items-center gap-0.5" aria-label="Primary">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.end}
                className={({ isActive }) =>
                  cx(
                    "relative rounded-lg px-2.5 py-1.5 text-[13px] transition-all duration-200",
                    isActive
                      ? "font-medium text-ink"
                      : "text-[#7C7160] hover:bg-sand/50 hover:text-ink",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {item.label}
                    {isActive && (
                      <span
                        aria-hidden
                        className="absolute inset-x-2.5 -bottom-[9px] h-[2px] rounded-full bg-brand"
                      />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex shrink-0 items-center gap-2 text-xs">
            <span aria-hidden className="h-1.5 w-1.5 animate-pulse rounded-full bg-olive" />
            <span className="hidden font-medium text-olivehi sm:inline">API connected</span>
            <span className="hidden font-mono text-[11px] text-[#A0927C] md:inline">
              localhost:8000 · mock
            </span>
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1200px] px-5 py-8 lg:px-6">
        <Routes>
          <Route path="/" element={<OverviewPage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/runs" element={<RunsPage />} />
          <Route path="/traces" element={<TracesPage />} />
          <Route path="/tools" element={<ToolsPage />} />
          <Route path="/sandbox" element={<SandboxPage />} />
          <Route path="/policies" element={<PoliciesPage />} />
          <Route path="/evaluations" element={<EvaluationsPage />} />
          <Route path="/experiments" element={<ExperimentsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<OverviewPage />} />
        </Routes>
      </main>
    </div>
  );
}
