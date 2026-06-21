/**
 * AgentLane (SOC theater, §F6) — one subagent's column: its 🦉 mascot, a title,
 * the latest `agent_status` line, and the row of ToolChips igniting/finishing.
 * Driven entirely by an `AgentLaneState` slice from the theater store.
 *
 * The two lanes are 🛡️ OWASP Scanner and 🤖 Agentic Surface Auditor
 * (05-agent-team). The owl is `running` while the lane has active tools and
 * flips to `alert` when a tool just failed (a hit). Dark SOC palette via tokens.
 */
"use client";

import { cn } from "@/src/application/lib/utils";
import type {
  AgentLaneState,
  TheaterRunStatus,
} from "@/src/application/owliver/stores/theater-store";
import { OwlMascot, type OwlState } from "@/src/presentation/owliver/components/owl-mascot";
import { ToolChip } from "@/src/presentation/owliver/theater/tool-chip";

export type AgentLaneProps = {
  lane: AgentLaneState;
  /** Display title, e.g. "OWASP Scanner". */
  title: string;
  /** Leading glyph (🛡️ / 🤖). */
  icon?: string;
  /** Overall run status — when terminal the owl rests. */
  runStatus?: TheaterRunStatus;
  className?: string;
};

function laneOwlState(
  lane: AgentLaneState,
  runStatus?: TheaterRunStatus
): OwlState {
  const tools = lane.toolOrder.map((t) => lane.tools[t]);
  if (tools.some((t) => t?.state === "failed")) return "alert";
  if (runStatus === "done" || runStatus === "cancelled" || runStatus === "error")
    return "idle";
  if (tools.some((t) => t?.state === "running")) return "running";
  return lane.status ? "running" : "idle";
}

export function AgentLane({
  lane,
  title,
  icon,
  runStatus,
  className,
}: AgentLaneProps) {
  const owl = laneOwlState(lane, runStatus);
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
        <OwlMascot state={owl} size={40} />
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
