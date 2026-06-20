import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";
import type { UserResponse } from "@/src/domain/responses/profile";
import type TaskResultResponse from "@/src/domain/responses/task-result";

export interface UpdateProfilePayload {
  firstName?: string | null;
  lastName?: string | null;
}

export interface UpdatePasswordPayload {
  currentPassword: string;
  newPassword: string;
}

export interface ProfileRepository {
  get(): Promise<UserResponse | ErrorFeeback>;
  update(payload: UpdateProfilePayload): Promise<UserResponse | ErrorFeeback>;
  updatePassword(
    payload: UpdatePasswordPayload
  ): Promise<TaskResultResponse | ErrorFeeback>;
}
