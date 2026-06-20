import type { Industry } from "@/src/domain/entities/industry";
import type { ErrorFeeback } from "@/src/domain/errors/error-feeback";

export interface IndustryRepository {
  list(): Promise<Industry[] | ErrorFeeback>;
}
