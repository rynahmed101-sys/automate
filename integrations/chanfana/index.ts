import { ApiException, fromHono } from "chanfana";
import { Hono } from "hono";
import { ContentfulStatusCode } from "hono/utils/http-status";
import { tasksRouter } from "./endpoints/tasks/router";
import { DummyEndpoint } from "./endpoints/dummyEndpoint";
import { workerRouter } from "./endpoints/worker/router";
import { consumeWorkerJob, QUEUE_RETRY_DELAY_SECONDS, type WorkerJobMessage } from "./worker/queue";
import { recoverStaleWorkerJobs } from "./worker/recovery";

const app = new Hono<{ Bindings: Env }>();
app.onError((err, c) => {
  if (err instanceof ApiException) return c.json({ success: false, errors: err.buildResponse() }, err.status as ContentfulStatusCode);
  console.error("Global error handler caught:", err);
  return c.json({ success: false, errors: [{ code: 7000, message: "Internal Server Error" }] }, 500);
});
const openapi = fromHono(app, { docs_url: "/", schema: { info: { title: "Automate Worker", version: "1.0.0", description: "Bounded machine-facing worker API for Automate capability jobs." } } });
openapi.route("/tasks", tasksRouter);
openapi.route("/worker/v1", workerRouter);
openapi.post("/dummy/:slug", DummyEndpoint);
export default {
  fetch: app.fetch,
  async queue(batch: MessageBatch<WorkerJobMessage>, env: Env): Promise<void> {
    for (const message of batch.messages) {
      const outcome = await consumeWorkerJob(env, message.body.jobId);
      if (outcome === "ack") message.ack(); else message.retry({ delaySeconds: QUEUE_RETRY_DELAY_SECONDS });
    }
  },
  async scheduled(_controller: ScheduledController, env: Env): Promise<void> { await recoverStaleWorkerJobs(env); },
} satisfies ExportedHandler<Env, WorkerJobMessage>;
