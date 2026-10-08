import type { WorkerJobMessage } from "./queue";
declare global {
  interface Env {
    AUTOMATE_JOB_QUEUE: Queue<WorkerJobMessage>;
    MIRROR_GITHUB_TOKEN?: string;
    MIRROR_GITHUB_REPOSITORY?: string;
    MIRROR_MISSION_WORKFLOW?: string;
    MIRROR_MISSION_REF?: string;
    VERIFICATION_ENGINE_JOB_TOKEN?: string;
    VERIFICATION_ENGINE_ENDPOINT?: string;
  }
}
export {};
