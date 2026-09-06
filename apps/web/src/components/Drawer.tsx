import type { ReactNode } from "react";
import { cx } from "./ui";

export function Drawer({
  open,
  onClose,
  title,
  subtitle,
  children,
  width = "max-w-2xl",
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  subtitle?: ReactNode;
  children: ReactNode;
  width?: string;
}) {
  return (
    <div className={cx("fixed inset-0 z-40", open ? "pointer-events-auto" : "pointer-events-none")}>
      {/* scrim */}
      <div
        onClick={onClose}
        className={cx(
          "absolute inset-0 bg-black/50 transition-opacity",
          open ? "opacity-100" : "opacity-0",
        )}
      />
      {/* panel */}
      <aside
        className={cx(
          "absolute right-0 top-0 flex h-full w-full flex-col border-l border-gray-800 bg-gray-950 shadow-2xl transition-transform",
          width,
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        <header className="flex items-start justify-between gap-3 border-b border-gray-800 px-5 py-4">
          <div className="min-w-0">
            <h2 className="truncate text-base font-semibold text-gray-50">{title}</h2>
            {subtitle && <div className="mt-0.5 text-xs text-gray-500">{subtitle}</div>}
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-gray-500 hover:bg-gray-800 hover:text-gray-200"
            aria-label="Close"
          >
            <svg viewBox="0 0 20 20" className="h-5 w-5" fill="currentColor">
              <path d="M6.3 5.2 10 8.9l3.7-3.7 1.1 1.1L11.1 10l3.7 3.7-1.1 1.1L10 11.1l-3.7 3.7-1.1-1.1L8.9 10 5.2 6.3l1.1-1.1z" />
            </svg>
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </aside>
    </div>
  );
}
