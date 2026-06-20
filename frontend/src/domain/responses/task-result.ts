import type { TaskResult } from "@/src/domain/entities/common/task-result";

export default interface TaskResultResponse {
  data: TaskResult;
  datetime: string;
}

export const successTask: TaskResultResponse = {
  data: {
    status: "SUCCESS",
    completedAt: new Date().toISOString(),
  },
  datetime: new Date().toISOString(),
};
