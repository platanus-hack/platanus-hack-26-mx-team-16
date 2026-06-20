export interface TaskResult {
  status: string;
  completedAt: string;
}

export function isSuccessfulTask(taskResult: TaskResult) {
  return taskResult.status === "SUCCESS";
}
