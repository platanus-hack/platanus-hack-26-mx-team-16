"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from "react";

import type {
  AnalysisRuleResult,
  AnalysisRun,
  AnalysisRunDetail,
  AnalysisRunEvent,
} from "@/src/domain/entities/analysis-run";
import { authHttp } from "@/src/infrastructure/http/client";
import { HttpAnalysisRunRepository } from "@/src/infrastructure/repositories/http-analysis-run";

interface State {
  history: AnalysisRun[];
  activeRun: AnalysisRun | null;
  results: AnalysisRuleResult[];
  totalEvaluations: number;
  completedEvaluations: number;
  error: string | null;
  isHydrated: boolean;
}

type Action =
  | { type: "LOAD_HISTORY"; runs: AnalysisRun[] }
  | { type: "LOAD_DETAIL"; detail: AnalysisRunDetail }
  | { type: "RUN_START"; run: AnalysisRun }
  | { type: "RUN_TOTAL"; total: number }
  | { type: "RESULT"; result: AnalysisRuleResult }
  | { type: "PROGRESS"; completed: number; total: number }
  | { type: "RUN_UPDATE"; run: AnalysisRun }
  | { type: "RUN_END"; status: AnalysisRun["status"]; error?: string | null }
  | { type: "ERROR"; message: string }
  | { type: "CLEAR_ERROR" };

const INITIAL_STATE: State = {
  history: [],
  activeRun: null,
  results: [],
  totalEvaluations: 0,
  completedEvaluations: 0,
  error: null,
  isHydrated: false,
};

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case "LOAD_HISTORY":
      return { ...state, history: action.runs, isHydrated: true };
    case "LOAD_DETAIL": {
      const results = action.detail.results ?? [];
      return {
        ...state,
        activeRun: action.detail,
        results,
        completedEvaluations: results.length,
        totalEvaluations: Math.max(state.totalEvaluations, results.length),
      };
    }
    case "RUN_START": {
      // Preserve history order when re-attaching to an existing run (selection
      // from the list or initial auto-attach). Only prepend when the run is
      // genuinely new (e.g. just started via startRun).
      const exists = state.history.some((r) => r.uuid === action.run.uuid);
      const history = exists ? state.history : [action.run, ...state.history];
      return {
        ...state,
        activeRun: action.run,
        results: [],
        totalEvaluations: 0,
        completedEvaluations: 0,
        error: null,
        history,
      };
    }
    case "RUN_TOTAL":
      return { ...state, totalEvaluations: action.total };
    case "RESULT": {
      const filtered = state.results.filter(
        (r) => r.uuid !== action.result.uuid
      );
      return { ...state, results: [...filtered, action.result] };
    }
    case "PROGRESS":
      return {
        ...state,
        completedEvaluations: action.completed,
        totalEvaluations: action.total,
      };
    case "RUN_UPDATE": {
      if (!state.activeRun || state.activeRun.uuid !== action.run.uuid) {
        return state;
      }
      const history = state.history.map((h) =>
        h.uuid === action.run.uuid ? action.run : h
      );
      return { ...state, activeRun: action.run, history };
    }
    case "RUN_END": {
      if (!state.activeRun) return state;
      const updated: AnalysisRun = {
        ...state.activeRun,
        status: action.status,
        error: action.error ?? state.activeRun.error,
      };
      const history = [
        updated,
        ...state.history.filter((h) => h.uuid !== updated.uuid),
      ];
      return { ...state, activeRun: updated, history };
    }
    case "ERROR":
      return { ...state, error: action.message };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

export interface UseAnalysisRunsResult {
  history: AnalysisRun[];
  activeRun: AnalysisRun | null;
  results: AnalysisRuleResult[];
  totalEvaluations: number;
  completedEvaluations: number;
  error: string | null;
  isHydrated: boolean;
  isLive: boolean;
  isStarting: boolean;
  isCanceling: boolean;
  startRun: () => Promise<void>;
  cancelRun: () => Promise<void>;
  forceCancelRun: () => Promise<void>;
  selectRun: (run: AnalysisRun) => void;
  clearError: () => void;
}

/**
 * Loads analysis-run history for a case, attaches to a live run when one exists,
 * and exposes `startRun` / `cancelRun` / `selectRun`. Single owner so the main
 * tab content and the bottom pane share a consistent view.
 */
export function useAnalysisRuns(
  workflowId: string,
  caseId: string
): UseAnalysisRunsResult {
  const repo = useMemo(() => new HttpAnalysisRunRepository(authHttp), []);
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const [isStarting, setIsStarting] = useState(false);
  const subscriptionRef = useRef<{ unsubscribe: () => void } | null>(null);

  const handleEvent = useCallback((event: AnalysisRunEvent) => {
    switch (event.type) {
      case "RUN_STARTED":
        dispatch({ type: "RUN_TOTAL", total: event.payload.totalEvaluations });
        break;
      case "RULE_RESULT_READY":
        dispatch({ type: "RESULT", result: event.payload });
        break;
      case "RUN_PROGRESS":
        dispatch({
          type: "PROGRESS",
          completed: event.payload.completed,
          total: event.payload.total,
        });
        break;
      case "RUN_COMPLETED":
        dispatch({ type: "RUN_END", status: "COMPLETED" });
        break;
      case "RUN_FAILED":
        dispatch({
          type: "RUN_END",
          status: "FAILED",
          error: event.payload.error,
        });
        break;
      case "RUN_CANCELED":
        dispatch({ type: "RUN_END", status: "CANCELED" });
        break;
    }
  }, []);

  const attachToRun = useCallback(
    (run: AnalysisRun) => {
      subscriptionRef.current?.unsubscribe();
      dispatch({ type: "RUN_START", run });
      repo.get(run.uuid).then((res) => {
        if ("data" in res) dispatch({ type: "LOAD_DETAIL", detail: res.data });
      });
      subscriptionRef.current = repo.subscribe(run.uuid, handleEvent);
    },
    [repo, handleEvent]
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const result = await repo.list(workflowId, caseId);
      if (cancelled) return;
      if ("data" in result) {
        dispatch({ type: "LOAD_HISTORY", runs: result.data });
        const live = result.data.find(
          (r) => r.status === "RUNNING" || r.status === "CANCELING"
        );
        // Backend returns runs sorted by created_at DESC, so result.data[0]
        // is the most recent. Attach to the live run if any, otherwise show
        // the latest historical run by default.
        if (live) attachToRun(live);
        else if (result.data.length > 0) attachToRun(result.data[0]);
      }
    })();
    return () => {
      cancelled = true;
      subscriptionRef.current?.unsubscribe();
      subscriptionRef.current = null;
    };
  }, [repo, workflowId, caseId, attachToRun]);

  const startRun = useCallback(async () => {
    setIsStarting(true);
    dispatch({ type: "CLEAR_ERROR" });
    const result = await repo.start(workflowId, caseId);
    setIsStarting(false);
    if ("data" in result) {
      attachToRun(result.data);
    } else {
      dispatch({
        type: "ERROR",
        message: result.errors?.[0]?.message ?? "Failed to start run.",
      });
    }
  }, [repo, workflowId, caseId, attachToRun]);

  const cancelRun = useCallback(async () => {
    if (!state.activeRun || state.activeRun.status !== "RUNNING") return;
    // Optimistic flip so the FE reflects the transition while the
    // backend signals Temporal and the workflow drains in-flight evals.
    dispatch({
      type: "RUN_UPDATE",
      run: { ...state.activeRun, status: "CANCELING" },
    });
    const result = await repo.cancel(state.activeRun.uuid);
    if ("data" in result) {
      dispatch({ type: "RUN_UPDATE", run: result.data });
    } else {
      // Revert on failure so the button doesn't stay stuck.
      dispatch({ type: "RUN_UPDATE", run: state.activeRun });
      dispatch({
        type: "ERROR",
        message: result.errors?.[0]?.message ?? "Failed to cancel run.",
      });
    }
  }, [repo, state.activeRun]);

  const forceCancelRun = useCallback(async () => {
    if (!state.activeRun) return;
    const result = await repo.forceCancel(state.activeRun.uuid);
    if ("data" in result) {
      dispatch({ type: "RUN_UPDATE", run: result.data });
    } else {
      dispatch({
        type: "ERROR",
        message:
          result.errors?.[0]?.message ?? "Failed to force-cancel run.",
      });
    }
  }, [repo, state.activeRun]);

  const clearError = useCallback(() => dispatch({ type: "CLEAR_ERROR" }), []);

  const isLive =
    state.activeRun?.status === "RUNNING" ||
    state.activeRun?.status === "CANCELING";
  const isCanceling = state.activeRun?.status === "CANCELING";

  return {
    history: state.history,
    activeRun: state.activeRun,
    results: state.results,
    totalEvaluations: state.totalEvaluations,
    completedEvaluations: state.completedEvaluations,
    error: state.error,
    isHydrated: state.isHydrated,
    isLive,
    isStarting,
    isCanceling,
    startRun,
    cancelRun,
    forceCancelRun,
    selectRun: attachToRun,
    clearError,
  };
}
