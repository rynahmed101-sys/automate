import type { WorkerPacketType, WorkerResultType } from "./contracts";

function underPrefix(path: string, prefixes: string[]) {
  const normalized = path.replace(/\\/g, "/").replace(/^\.\//, "");
  return prefixes.some((prefix) => {
    const clean = prefix.replace(/\\/g, "/").replace(/\/$/, "");
    return normalized === clean || normalized.startsWith(clean + "/");
  });
}

const secretPatterns = [
  /(api[_-]?key|secret|password|token)\s*[:=]\s*[^\s,]+/i,
  /-----BEGIN [A-Z ]+ PRIVATE KEY-----/i,
];

export function validateWorkerResultAgainstPacket(
  packet: WorkerPacketType["packet"],
  result: WorkerResultType,
): string[] {
  const errors: string[] = [];

  if (result.request_id !== packet.request_id) {
    errors.push("request_id does not match worker packet");
  }

  for (const change of result.changes) {
    if (change.operation === "update" && typeof change.expected_sha !== "string") {
      errors.push("update change is missing expected_sha: " + change.path);
    }
    if (change.operation === "create" && change.expected_sha !== null) {
      errors.push("create change must use null expected_sha: " + change.path);
    }
    if (!underPrefix(change.path, packet.constraints.allowed_path_prefixes)) {
      errors.push("change outside allowed capability paths: " + change.path);
    }
    if (packet.constraints.forbidden_paths.includes(change.path)) {
      errors.push("change touches forbidden control-plane path: " + change.path);
    }
    if (change.content && secretPatterns.some((pattern) => pattern.test(change.content))) {
      errors.push("change appears to contain a secret-like value: " + change.path);
    }
  }

  for (const claim of result.claims ?? []) {
    if (claim.supported && claim.claim.toLowerCase().includes("certif")) {
      errors.push("worker cannot self-certify a capability");
    }
  }

  if (result.changes.length > packet.constraints.max_files) {
    errors.push("worker exceeded maximum allowed change count");
  }

  return errors;
}
