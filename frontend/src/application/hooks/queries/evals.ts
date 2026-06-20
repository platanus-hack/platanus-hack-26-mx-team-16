import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { authHttp } from "@/src/infrastructure/http/client";

export interface EvalDataset {
  uuid: string;
  name: string;
  pipelineSlug: string;
  createdAt: string | null;
}

export interface EvalRunMetrics {
  count: number;
  accuracy: number;
}

export interface EvalRun {
  uuid: string;
  datasetId: string;
  pipelineVersion: number;
  status: string;
  metrics: EvalRunMetrics;
}

export interface CreateDatasetInput {
  name: string;
  pipelineSlug: string;
}

export interface CreateRunInput {
  datasetId: string;
  pipelineVersion: number;
}

type Envelope<T> = { data: T } | { errors: { message: string }[] };

const BASE = "/v1/evals";

const api = {
  listDatasets: async (): Promise<Envelope<EvalDataset[]>> =>
    (await authHttp.get(`${BASE}/datasets`)).data,
  createDataset: async (
    input: CreateDatasetInput,
  ): Promise<Envelope<EvalDataset>> =>
    (
      await authHttp.post(`${BASE}/datasets`, {
        name: input.name,
        pipeline_slug: input.pipelineSlug,
      })
    ).data,
  createRun: async (input: CreateRunInput): Promise<Envelope<EvalRun>> =>
    (
      await authHttp.post(`${BASE}/runs`, {
        dataset_id: input.datasetId,
        pipeline_version: input.pipelineVersion,
      })
    ).data,
};

const KEY = ["eval-datasets"] as const;

export function useEvalDatasetsQuery() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () => {
      const res = await api.listDatasets();
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}

export function useCreateDatasetMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateDatasetInput) => {
      const res = await api.createDataset(input);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useCreateRunMutation() {
  return useMutation({
    mutationFn: async (input: CreateRunInput) => {
      const res = await api.createRun(input);
      if ("errors" in res) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });
}
