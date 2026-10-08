import type { Context, Next } from "hono";

export async function requireWorkerAuth(c: Context<{ Bindings: Env }>, next: Next) {
  const authorization = c.req.header("Authorization") ?? "";
  const expected = c.env.WORKER_API_SECRET;

  if (!expected || authorization !== "Bearer " + expected) {
    return c.json({ success: false, error: "Unauthorized" }, 401);
  }

  await next();
}
