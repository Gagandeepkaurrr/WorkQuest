import type { components } from "../generated/api-types";
export type Mission = components["schemas"]["MissionView"];
export type BranchState = components["schemas"]["BranchState"];
export type WorldState = components["schemas"]["VisibleWorldState"];
export type Action = components["schemas"]["VisibleAction"];
export type Artifact = components["schemas"]["ArtifactMetadata"];
export type CommandResponse = components["schemas"]["CommandResponse"];
export type RunSummary = components["schemas"]["RunView"];
export type Event = components["schemas"]["EventView"];
export const label = (s: string) =>
  s.replaceAll("_", " ").replaceAll(".", " › ");
export const display = (v: unknown) =>
  typeof v === "boolean"
    ? v
      ? "Enabled"
      : "Disabled"
    : typeof v === "object"
      ? JSON.stringify(v)
      : String(v ?? "—");
