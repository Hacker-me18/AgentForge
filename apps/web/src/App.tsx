import { NavLink, Route, Routes } from "react-router-dom";

const NAV_ITEMS = [
  { path: "/", label: "Overview" },
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

function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold text-gray-100">{title}</h1>
      <p className="mt-2 text-sm text-gray-400">Coming in Phase H.</p>
    </div>
  );
}

export default function App() {
  return (
    <div className="flex h-screen bg-gray-950 text-gray-100">
      <aside className="w-56 shrink-0 border-r border-gray-800 bg-gray-900">
        <div className="border-b border-gray-800 px-5 py-4">
          <div className="text-lg font-bold tracking-tight">AgentOS</div>
          <div className="text-xs text-gray-500">Agent Runtime &amp; Eval Platform</div>
        </div>
        <nav className="flex flex-col gap-0.5 p-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-gray-800 font-medium text-white"
                    : "text-gray-400 hover:bg-gray-800/60 hover:text-gray-200"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto">
        <Routes>
          {NAV_ITEMS.map((item) => (
            <Route
              key={item.path}
              path={item.path}
              element={<PlaceholderPage title={item.label} />}
            />
          ))}
        </Routes>
      </main>
    </div>
  );
}
