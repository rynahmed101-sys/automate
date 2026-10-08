import type { MirrorMissionEnvelopeType } from "./mirrorMissionEnvelope";

const API = "https://api.github.com";
const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

function githubHeaders(token: string): HeadersInit {
  return {
    accept: "application/vnd.github+json",
    authorization: "Bearer " + token,
    "x-github-api-version": "2022-11-28",
    "content-type": "application/json",
    "user-agent": "chanfana-mirror-handoff",
  };
}

async function github<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(API + path, {
    ...init,
    headers: { ...githubHeaders(token), ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const body = (await response.text()).slice(-4000);
    throw new Error("GitHub API " + response.status + ": " + body);
  }
  return (await response.json()) as T;
}

function exactMissionResult(logs: string, maxBytes: number): Record<string, unknown> {
  const begin = logs.lastIndexOf("MIRROR_RESULT_BEGIN");
  const end = logs.lastIndexOf("MIRROR_RESULT_END");
  if (begin < 0 || end <= begin) throw new Error("Mirror mission result markers were not found in workflow logs");
  const body = logs.slice(begin + "MIRROR_RESULT_BEGIN".length, end).trim();
  if (new TextEncoder().encode(body).byteLength > maxBytes) {
    throw new Error("Mirror mission result exceeds bounded payload size");
  }
  const parsed = JSON.parse(body) as Record<string, unknown>;
  if (parsed.authority !== "UNTRUSTED_MIRROR_PROPOSAL") {
    throw new Error("Mirror mission result failed closed authority check");
  }
  return parsed;
}

type WorkflowRun = {
  id: number;
  status: string;
  conclusion: string | null;
  created_at: string;
  html_url?: string;
};

type Job = { id: number; status: string; conclusion: string | null };

type WorkflowRuns = { workflow_runs: WorkflowRun[] };
type Jobs = { jobs: Job[] };

export async function executeMirrorMission(
  env: Env,
  mission: MirrorMissionEnvelopeType,
): Promise<Record<string, unknown>> {
  const token = env.MIRROR_GITHUB_TOKEN?.trim();
  if (!token) throw new Error("MIRROR_GITHUB_TOKEN is not configured");
  const configuredRepo = env.MIRROR_GITHUB_REPOSITORY?.trim();
  if (!configuredRepo || configuredRepo !== mission.target.repository) {
    throw new Error("Mirror mission repository is not allowlisted");
  }

  const startedAt = Date.now();
  const dispatchTime = new Date().toISOString();
  const payload = {
    ref: mission.target.ref,
    inputs: { mission_json: JSON.stringify(mission.mission) },
  };
  await github<unknown>(
    token,
    "/repos/" + mission.target.repository + "/actions/workflows/" +
      encodeURIComponent(mission.target.workflow) + "/dispatches",
    { method: "POST", body: JSON.stringify(payload) },
  );

  let run: WorkflowRun | undefined;
  const deadline = startedAt + mission.limits.deadline_ms;
  while (Date.now() < deadline) {
    const runs = await github<WorkflowRuns>(
      token,
      "/repos/" + mission.target.repository + "/actions/workflows/" +
        encodeURIComponent(mission.target.workflow) +
        "/runs?event=workflow_dispatch&branch=" +
        encodeURIComponent(mission.target.ref) + "&per_page=10",
    );
    run = runs.workflow_runs
      .filter((candidate) => candidate.created_at >= dispatchTime)
      .sort((a, b) => b.id - a.id)[0];
    if (run && run.status === "completed") break;
    await sleep(3000);
  }
  if (!run) throw new Error("Mirror mission workflow run was not observed before deadline");
  if (run.status !== "completed") throw new Error("Mirror mission workflow timed out");
  if (run.conclusion !== "success") {
    throw new Error("Mirror mission workflow concluded " + String(run.conclusion));
  }

  const jobs = await github<Jobs>(
    token,
    "/repos/" + mission.target.repository + "/actions/runs/" + run.id + "/jobs?per_page=20",
  );
  const completed = jobs.jobs.find((job) => job.conclusion === "success");
  if (!completed) throw new Error("Mirror mission has no successful execution job");

  const logResponse = await fetch(
    API + "/repos/" + mission.target.repository + "/actions/jobs/" + completed.id + "/logs",
    { headers: githubHeaders(token) },
  );
  if (!logResponse.ok) throw new Error("Unable to retrieve Mirror mission job logs");
  const logs = await logResponse.text();
  const result = exactMissionResult(logs, mission.limits.max_response_bytes);

  return {
    schema_version: "mirror.mission_result_ack.v1",
    authority: "UNTRUSTED_MIRROR_TRANSPORT",
    request_id: mission.request_id,
    source_revision: mission.source_revision,
    correlation_id: mission.provenance.correlation_id,
    workflow_run_id: run.id,
    workflow_url: run.html_url ?? null,
    mission_result: result,
    received_at: new Date().toISOString(),
  };
}
