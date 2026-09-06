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

const NAV_ITEMS = [
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

export default function App() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <aside className="flex w-56 shrink-0 flex-col border-r border-gray-800 bg-gray-900">
        <div className="border-b border-gray-800 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/15 ring-1 ring-emerald-500/40">
              <svg viewBox="0 0 24 24" className="h-4.5 w-4.5 text-emerald-400" fill="currentColor" style={{ width: 18, height: 18 }}>
                <path d="M4 5a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5zm7 3.2-1.2-2-1.6 1 1.2 2H7.2a.8.8 0 0 0 0 1.6h2.2L8.2 13l1.6 1 1.2-2 1.2 2 1.6-1-1.2-2.2h2.2a.8.8 0 1 0 0-1.6h-2.2l1.2-2-1.6-1-1.2 2z" transform="translate(0 -2)" />
              </svg>
            </div>
            <div>
              <div className="text-[15px] font-bold tracking-tight text-gray-50">AgentOS</div>
              <div className="text-[10.5px] text-gray-500">Agent Runtime · Eval · Studio</div>
            </div>
          </div>
        </div>
        <nav className="flex flex-1 flex-col gap-0.5 overflow-y-auto p-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-gray-800 font-medium text-white"
                    : "text-gray-400 hover:bg-gray-800/60 hover:text-gray-200"
                }`
              }
            >
              <span className="h-1 w-1 rounded-full bg-gray-600" />
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="border-t border-gray-800 px-5 py-3">
          <div className="flex items-center gap-1.5 text-[11px] text-gray-600">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400" />
            API connected
          </div>
          <div className="mt-0.5 font-mono text-[10px] text-gray-700">localhost:8000 · mock LLM</div>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl px-6 py-6">
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
        </div>
      </main>
    </div>
  );
}
