import {
  useBackgroundTasksStore,
  BackgroundTaskStatus,
} from "@/src/application/stores/background-tasks-store";

export function useDoctypeTaskActions(doctypeId: string) {
  const findPendingTask = (entityType: string) =>
    useBackgroundTasksStore
      .getState()
      .tasks.find(
        (t) =>
          t.entityId === doctypeId &&
          t.entityType === entityType &&
          t.status === BackgroundTaskStatus.Pending
      );

  const startTaskFor = (entityType: string, label: string, entityLabel?: string) =>
    useBackgroundTasksStore.getState().addTask({
      label,
      entityId: doctypeId,
      entityType,
      entityLabel,
    });

  const completeTaskFor = (entityType: string) => {
    const task = findPendingTask(entityType);
    if (task) useBackgroundTasksStore.getState().completeTask(task.id);
  };

  const errorTaskFor =
    (entityType: string, fallback: string) => (error?: string | null) => {
      const task = findPendingTask(entityType);
      if (task)
        useBackgroundTasksStore
          .getState()
          .errorTask(task.id, error ?? fallback);
    };

  return { findPendingTask, startTaskFor, completeTaskFor, errorTaskFor };
}
