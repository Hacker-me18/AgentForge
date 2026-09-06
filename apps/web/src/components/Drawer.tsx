import { useEffect, useId, useRef } from "react";
import type { ReactNode } from "react";
import { X } from "lucide-react";
import { cx } from "./ui";

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Right-slide detail panel that behaves as a modal dialog: focus moves in on
 * open, is trapped while open, Escape closes, and focus returns on close. When
 * closed the panel is inert + aria-hidden, so nothing inside is reachable.
 */
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
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const restoreRef = useRef<HTMLElement | null>(null);

  // Make the closed panel non-interactive and invisible to assistive tech.
  useEffect(() => {
    const el = panelRef.current;
    if (el) {
      el.inert = !open;
      el.setAttribute("aria-hidden", String(!open));
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;

    restoreRef.current = (document.activeElement as HTMLElement) ?? null;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const frame = window.requestAnimationFrame(() => {
      const first = firstFocusable(panelRef.current);
      (first ?? closeRef.current)?.focus();
    });

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab") return;
      const nodes = panelFocusables(panelRef.current);
      if (nodes.length === 0) return;
      const active = document.activeElement as HTMLElement | null;
      const idx = nodes.indexOf(active as HTMLElement);
      if (e.shiftKey && (idx <= 0 || !panelContains(active))) {
        e.preventDefault();
        nodes[nodes.length - 1].focus();
      } else if (!e.shiftKey && (idx === nodes.length - 1 || !panelContains(active))) {
        e.preventDefault();
        nodes[0].focus();
      }
    };

    document.addEventListener("keydown", onKeyDown, true);
    return () => {
      document.removeEventListener("keydown", onKeyDown, true);
      window.cancelAnimationFrame(frame);
      document.body.style.overflow = prevOverflow;
      restoreRef.current?.focus?.();
      restoreRef.current = null;
    };
  }, [open]);

  return (
    <div className={cx("fixed inset-0 z-50", open ? "pointer-events-auto" : "pointer-events-none")}>
      {/* scrim — warm brown haze, never pure black */}
      <div
        aria-hidden
        onClick={onClose}
        className={cx(
          "absolute inset-0 bg-[#2D2A24]/55 transition-opacity duration-200",
          open ? "opacity-100" : "opacity-0",
        )}
      />
      {/* panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cx(
          "absolute inset-y-0 right-0 flex w-full flex-col border-l border-edge bg-panel shadow-lifted outline-none transition-transform duration-200 ease-out",
          width,
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        <header className="flex items-start justify-between gap-3 border-b border-edge/80 px-5 py-3.5">
          <div className="min-w-0">
            <h2
              id={titleId}
              className="truncate font-serif text-[17px] font-medium leading-snug tracking-tight text-ink"
            >
              {title}
            </h2>
            {subtitle && <div className="mt-0.5 truncate text-xs text-[#8A7C69]">{subtitle}</div>}
          </div>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Close panel"
            className="-mr-1.5 -mt-1 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[#8A7C69] hover:bg-sand/60 hover:text-ink"
          >
            <X aria-hidden className="h-4 w-4" />
          </button>
        </header>
        <div className="flex-1 overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

function panelContains(el: HTMLElement | null): boolean {
  return !!el && typeof el.closest === "function" && !!el.closest('[role="dialog"]');
}

function panelFocusables(panel: HTMLElement | null): HTMLElement[] {
  if (!panel) return [];
  return Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => !el.hasAttribute("disabled") && el.offsetParent !== null,
  );
}

function firstFocusable(panel: HTMLElement | null): HTMLElement | null {
  return panelFocusables(panel)[0] ?? null;
}
