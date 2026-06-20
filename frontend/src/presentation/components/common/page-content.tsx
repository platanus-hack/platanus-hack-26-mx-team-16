"use client";

import {
  ArrowLeft,
  ChevronDown,
  ChevronUp,
  Maximize2,
  type LucideIcon,
} from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { cn } from "@/src/application/lib/utils";

// LiveBottomPane.Header is a deterministic toggle bar (px-5 py-2.5 + 24px size
// buttons). Body reserves this much space at the bottom so its scrollable area
// never hides content behind the pinned pane header.
const LIVE_BOTTOM_PANE_HEADER_PX = 48;

interface PageContentCtxValue {
  hasLiveBottomPane: boolean;
  /** Returns the unregister function for use as a useEffect cleanup. */
  registerLiveBottomPane: () => () => void;
}

const PageContentCtx = createContext<PageContentCtxValue>({
  hasLiveBottomPane: false,
  registerLiveBottomPane: () => () => {},
});

interface PageContentProps {
  children: ReactNode;
  className?: string;
}

export function PageContent({ children, className }: PageContentProps) {
  const [count, setCount] = useState(0);
  const registerLiveBottomPane = useCallback(() => {
    setCount((c) => c + 1);
    return () => setCount((c) => Math.max(0, c - 1));
  }, []);

  const value = useMemo<PageContentCtxValue>(
    () => ({
      hasLiveBottomPane: count > 0,
      registerLiveBottomPane,
    }),
    [count, registerLiveBottomPane]
  );

  return (
    <PageContentCtx.Provider value={value}>
      <div
        className={cn(
          "relative flex h-full min-h-0 flex-col overflow-hidden",
          className
        )}
      >
        {children}
      </div>
    </PageContentCtx.Provider>
  );
}

/**
 * Reserved bottom padding (in px) any descendant should leave clear so it does
 * not slide under the pinned LiveBottomPane.Header. 0 when no pane is mounted.
 */
export function usePageContentBottomInset(): number {
  const { hasLiveBottomPane } = useContext(PageContentCtx);
  return hasLiveBottomPane ? LIVE_BOTTOM_PANE_HEADER_PX : 0;
}

interface PageContentHeaderProps {
  icon?: LucideIcon;
  title: ReactNode;
  subtitle?: ReactNode;
  showBack?: boolean;
  onBack?: () => void;
  actions?: ReactNode;
  className?: string;
  children?: ReactNode;
}

function PageContentHeader({
  icon: Icon,
  title,
  subtitle,
  showBack,
  onBack,
  actions,
  children,
  className,
}: PageContentHeaderProps) {
  return (
    <header
      className={cn(
        "flex shrink-0 items-center gap-4 px-6 pt-6 mb-6",
        className,
      )}
    >
      {showBack && (
        <button
          type="button"
          onClick={onBack}
          aria-label="Go back"
          className="flex h-8 w-8 shrink-0 cursor-pointer items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
      )}
      {Icon && (
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Icon className="h-5 w-5" />
        </div>
      )}
      <div className="flex min-w-0 flex-col gap-0.5">
        {typeof title === "string" ? (
          <h1 className="truncate text-xl font-semibold leading-tight">
            {title}
          </h1>
        ) : (
          title
        )}
        {subtitle != null &&
          (typeof subtitle === "string" ? (
            <p className="truncate font-mono text-xs tracking-wide text-muted-foreground">
              {subtitle}
            </p>
          ) : (
            subtitle
          ))}
      </div>
      {children}
      {actions && (
        <div className="ml-auto flex shrink-0 items-center gap-2">
          {actions}
        </div>
      )}
    </header>
  );
}

interface PageContentBodyProps {
  children: ReactNode;
  className?: string;
  scroll?: boolean;
}

function PageContentBody({
  children,
  className,
  scroll = true,
}: PageContentBodyProps) {
  const inset = usePageContentBottomInset();
  return (
    <div
      style={inset > 0 ? { paddingBottom: inset } : undefined}
      className={cn(
        "flex min-h-0 flex-1 flex-col px-6 pb-6",
        scroll ? "overflow-y-auto" : "overflow-hidden",
        className
      )}
    >
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// LiveBottomPane — compound component
// ---------------------------------------------------------------------------
//
// Layout states:
//   • "min"      → just the header row (collapsed)
//   • "expanded" → max(500px, 30vh) tall, anchored at bottom of PageContent
//   • "max"      → absolutely covers all of PageContent
//
// Composition:
//   <PageContent.LiveBottomPane defaultSize="expanded">
//     <PageContent.LiveBottomPane.Header icon={Radio} title="…" label="…">
//       {/* extra right-side meta (e.g. connection pill) */}
//     </PageContent.LiveBottomPane.Header>
//     <PageContent.LiveBottomPane.Content>
//       {/* scrollable body, hidden when size === "min" */}
//     </PageContent.LiveBottomPane.Content>
//   </PageContent.LiveBottomPane>

export enum PaneSize {
  Min = "min",
  Expanded = "expanded",
  Max = "max",
}

interface PaneSizeContextValue {
  size: PaneSize;
  setSize: (size: PaneSize) => void;
}

const PaneSizeContext = createContext<PaneSizeContextValue | null>(null);

function usePaneSize(): PaneSizeContextValue {
  const ctx = useContext(PaneSizeContext);
  if (!ctx) {
    throw new Error(
      "LiveBottomPane.Header / .Content must be used inside <PageContent.LiveBottomPane>"
    );
  }
  return ctx;
}

interface LiveBottomPaneProps {
  children: ReactNode;
  className?: string;
  defaultSize?: PaneSize;
  size?: PaneSize;
  onSizeChange?: (size: PaneSize) => void;
}

function LiveBottomPane({
  children,
  className,
  defaultSize = PaneSize.Expanded,
  size: controlledSize,
  onSizeChange,
}: LiveBottomPaneProps) {
  const [internalSize, setInternalSize] = useState<PaneSize>(defaultSize);
  const isControlled = controlledSize !== undefined;
  const size = isControlled ? controlledSize : internalSize;
  const setSize = useCallback(
    (next: PaneSize) => {
      if (!isControlled) setInternalSize(next);
      onSizeChange?.(next);
    },
    [isControlled, onSizeChange]
  );
  const value = useMemo<PaneSizeContextValue>(
    () => ({ size, setSize }),
    [size, setSize]
  );

  // Tell the surrounding PageContent that a pane is mounted so its Body
  // (and any other content using usePageContentBottomInset) leaves room.
  const { registerLiveBottomPane } = useContext(PageContentCtx);
  useEffect(() => registerLiveBottomPane(), [registerLiveBottomPane]);

  const isMax = size === PaneSize.Max;
  const isExpanded = size === PaneSize.Expanded;

  return (
    <PaneSizeContext.Provider value={value}>
      <section
        data-size={size}
        aria-label="Live activity panel"
        className={cn(
          "flex flex-col overflow-hidden",
          isMax
            ? "absolute inset-0 z-[200] bg-card"
            : "absolute inset-x-0 bottom-0 z-10 border-t border-border/60 bg-card/65 backdrop-blur-sm shadow-[0_-8px_24px_-12px_rgb(0_0_0_/_0.12)]",
          className
        )}
        style={isExpanded ? { height: "max(500px, 30vh)" } : undefined}
      >
        {children}
      </section>
    </PaneSizeContext.Provider>
  );
}

interface LivePaneHeaderProps {
  icon?: LucideIcon;
  title: ReactNode;
  label?: ReactNode;
  children?: ReactNode;
  className?: string;
}

function LivePaneHeader({
  icon: Icon,
  title,
  label,
  children,
  className,
}: LivePaneHeaderProps) {
  const { size, setSize } = usePaneSize();
  const toggle = useCallback(() => {
    setSize(size === PaneSize.Min ? PaneSize.Expanded : PaneSize.Min);
  }, [size, setSize]);

  return (
    <header
      onClick={toggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          toggle();
        }
      }}
      role="button"
      tabIndex={0}
      aria-expanded={size !== PaneSize.Min}
      aria-label={size === PaneSize.Min ? "Expandir panel" : "Minimizar panel"}
      className={cn(
        "flex shrink-0 cursor-pointer items-center gap-3 bg-card/85 px-5 py-2.5",
        "transition-colors hover:bg-muted/40",
        "focus-visible:outline-none focus-visible:bg-muted/40",
        className
      )}
    >
      <div className="flex min-w-0 flex-1 items-center gap-3">
        {Icon ? (
          <Icon
            className="h-3.5 w-3.5 shrink-0 text-muted-foreground"
            aria-hidden
          />
        ) : null}
        {typeof title === "string" ? (
          <h2 className="truncate text-sm font-semibold tracking-tight">
            {title}
          </h2>
        ) : (
          title
        )}
        {label != null ? (
          typeof label === "string" ? (
            <span className="truncate font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground tabular-nums">
              {label}
            </span>
          ) : (
            label
          )
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {children}
        <PaneSizeControls />
      </div>
    </header>
  );
}

interface LivePaneContentProps {
  children: ReactNode;
  className?: string;
}

function LivePaneContent({ children, className }: LivePaneContentProps) {
  const { size } = usePaneSize();
  if (size === PaneSize.Min) return null;

  return (
    <div
      className={cn(
        "min-h-0 flex-1 overflow-y-auto overscroll-contain border-t border-border/40",
        // subtle scrollbar (firefox + webkit)
        "[scrollbar-width:thin]",
        "[&::-webkit-scrollbar]:w-1.5",
        "[&::-webkit-scrollbar-track]:bg-transparent",
        "[&::-webkit-scrollbar-thumb]:rounded-full",
        "[&::-webkit-scrollbar-thumb]:bg-border",
        "hover:[&::-webkit-scrollbar-thumb]:bg-muted-foreground/40",
        className
      )}
    >
      {children}
    </div>
  );
}

function PaneSizeControls() {
  const { size, setSize } = usePaneSize();

  const goMin = useCallback(() => setSize(PaneSize.Min), [setSize]);
  const goExpanded = useCallback(() => setSize(PaneSize.Expanded), [setSize]);
  const goMax = useCallback(() => setSize(PaneSize.Max), [setSize]);

  return (
    <div
      role="group"
      aria-label="Tamaño del panel"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
      className={cn(
        "flex items-center gap-px rounded-md p-0.5",
        "bg-muted/40 ring-1 ring-inset ring-border/40"
      )}
    >
      <SizeButton
        active={size === PaneSize.Min}
        onClick={goMin}
        label="Minimizar"
        icon={ChevronDown}
      />
      <SizeButton
        active={size === PaneSize.Expanded}
        onClick={goExpanded}
        label="Expandir"
        icon={ChevronUp}
      />
      <SizeButton
        active={size === PaneSize.Max}
        onClick={goMax}
        label="Maximizar"
        icon={Maximize2}
      />
    </div>
  );
}

interface SizeButtonProps {
  active: boolean;
  onClick: () => void;
  label: string;
  icon: LucideIcon;
}

function SizeButton({ active, onClick, label, icon: Icon }: SizeButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      aria-pressed={active}
      title={label}
      className={cn(
        "relative flex h-6 w-7 cursor-pointer items-center justify-center rounded-sm",
        "transition-[background-color,color,box-shadow] duration-150",
        "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-foreground/40",
        active
          ? "bg-background text-foreground shadow-sm ring-1 ring-inset ring-border/60"
          : "text-muted-foreground/70 hover:bg-background/50 hover:text-foreground"
      )}
    >
      <Icon
        className="h-3.5 w-3.5"
        strokeWidth={active ? 2.25 : 1.75}
        aria-hidden
      />
    </button>
  );
}

LiveBottomPane.Header = LivePaneHeader;
LiveBottomPane.Content = LivePaneContent;

PageContent.Header = PageContentHeader;
PageContent.Body = PageContentBody;
PageContent.LiveBottomPane = LiveBottomPane;
