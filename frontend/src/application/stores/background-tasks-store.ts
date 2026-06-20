import { create } from "zustand";

export const BackgroundTaskStatus = {
  Pending: "pending",
  Completed: "completed",
  Error: "error",
} as const;

export type BackgroundTaskStatus = typeof BackgroundTaskStatus[keyof typeof BackgroundTaskStatus];

export interface BackgroundTask {
  id: string;
  label: string;
  status: BackgroundTaskStatus;
  entityId: string;
  entityType: string;
  entityLabel?: string;
  errorMessage?: string;
}

interface BackgroundTasksStore {
  tasks: BackgroundTask[];
  addTask: (task: Omit<BackgroundTask, "id" | "status">) => string;
  completeTask: (id: string) => void;
  errorTask: (id: string, message?: string) => void;
  removeTask: (id: string) => void;
}

// If no terminal SSE event arrives (e.g. frontend reconnected mid-flight and
// missed the completion event), discard the task automatically after this delay.
const MAX_PENDING_MS = 10_000;

export const useBackgroundTasksStore = create<BackgroundTasksStore>((set, get) => ({
  tasks: [],

  addTask: (task) => {
    const existing = get().tasks.find(
      (t) =>
        t.entityId === task.entityId &&
        t.entityType === task.entityType &&
        t.status === BackgroundTaskStatus.Pending
    );
    if (existing) return existing.id;

    const id = crypto.randomUUID();
    set((s) => ({
      tasks: [...s.tasks, { ...task, id, status: BackgroundTaskStatus.Pending }],
    }));
    setTimeout(() => {
      set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) }));
    }, MAX_PENDING_MS);
    return id;
  },

  completeTask: (id) =>
    set((s) => ({
      tasks: s.tasks.map((t) =>
        t.id === id ? { ...t, status: BackgroundTaskStatus.Completed } : t
      ),
    })),

  errorTask: (id, message) =>
    set((s) => ({
      tasks: s.tasks.map((t) =>
        t.id === id ? { ...t, status: BackgroundTaskStatus.Error, errorMessage: message } : t
      ),
    })),

  removeTask: (id) =>
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) })),
}));
