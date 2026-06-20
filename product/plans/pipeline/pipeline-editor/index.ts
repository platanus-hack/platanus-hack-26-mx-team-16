// index.ts — barrel for the Pipeline Editor.
export { PipelineEditor, default } from "./pipeline-editor";
export type { PipelineEditorProps } from "./pipeline-editor";

export { usePipeline } from "./use-pipeline";
export type { UsePipelineOptions, UsePipelineReturn } from "./use-pipeline";

export { computeLayout, validatePipeline, edgePath, DIMS } from "./layout";
export type { Layout, Block, Edge, Dims } from "./layout";

export { getAccent, accentVars } from "./accents";
export type { Accent } from "./accents";

export { PipeIcon } from "./icons";

export {
  SAMPLE_STAGES, SAMPLE_INITIAL_STATE, SAMPLE_ADDABLE,
} from "./sample-data";

export { DEFAULT_APPEARANCE } from "./types";
export type {
  Stage, Phase, ConfigField, FieldType, Scope, StageType, StageLayout,
  AccentName, Appearance, NodeStyle, Density, EdgeStyle, Palette, Background,
  PipelineState, Selection, ValidationMessage, ValidationLevel,
  ConfigOverrides, IconName,
} from "./types";
