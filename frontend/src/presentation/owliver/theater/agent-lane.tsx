/**
 * AgentLane (SOC theater, §F6) — one subagent's column: its Owliver eyes mark, a title,
 * the latest `agent_status` line, and the row of ToolChips igniting/finishing.
 * Driven entirely by an `AgentLaneState` slice from the theater store.
 *
 * The two lanes are 🛡️ OWASP Scanner and 🤖 Agentic Surface Auditor
 * (05-agent-team). Tool state is reported by the chips and latest status line.
 * Dark SOC palette via tokens.
 */
"use client";

import type { ReactNode } from "react";

import { cn } from "@/src/application/lib/utils";
import type {
  AgentLaneState,
  TheaterRunStatus,
} from "@/src/application/owliver/stores/theater-store";
import { ToolChip } from "@/src/presentation/owliver/theater/tool-chip";

export type AgentLaneProps = {
  lane: AgentLaneState;
  /** Display title, e.g. "OWASP Scanner". */
  title: string;
  /** Leading icon (ShieldWeb / AgenticChip). */
  icon?: ReactNode;
  /** Overall run status — when terminal the owl rests. */
  runStatus?: TheaterRunStatus;
  className?: string;
};

function AgentLaneMark({ size = 40 }: { size?: number }) {
  return (
    <span
      aria-hidden
      className="relative inline-block shrink-0 select-none"
      style={{ width: size, height: size }}
    >
      {/* biome-ignore lint/performance/noImgElement: small route-scoped brand PNG. */}
      <img
        src="/owliver_eyes_black.png"
        alt=""
        width={size}
        height={size}
        className="block object-contain dark:hidden [.soc_&]:hidden"
      />
      {/* biome-ignore lint/performance/noImgElement: small route-scoped brand PNG. */}
      <img
        src="/owliver_eyes_white.png"
        alt=""
        width={size}
        height={size}
        className="absolute inset-0 hidden object-contain dark:block [.soc_&]:block"
      />
    </span>
  );
}

export function AgentLane({ lane, title, icon, className }: AgentLaneProps) {
  const tools = lane.toolOrder.map((t) => lane.tools[t]).filter(Boolean);

  return (
    <section
      data-slot="agent-lane"
      data-lane={lane.id}
      className={cn(
        "flex flex-col gap-3 rounded-2xl border border-outline-variant bg-surface-container-low p-4",
        className
      )}
    >
      <header className="flex items-center gap-3">
        <AgentLaneMark size={40} />
        <div className="min-w-0">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            {icon && <span aria-hidden>{icon}</span>}
            {title}
          </h3>
          <p className="truncate text-xs text-on-surface-variant">
            {lane.status || "En espera…"}
          </p>
        </div>
      </header>

      {tools.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {tools.map((t) => (
            <ToolChip key={t.tool} tool={t.tool} state={t.state} />
          ))}
        </div>
      )}
    </section>
  );
}
