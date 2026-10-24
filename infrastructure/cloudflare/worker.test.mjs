import test from "node:test";
import assert from "node:assert/strict";
import worker, { tick } from "./worker.mjs";

const env = { GITHUB_DISPATCH_TOKEN: "fake-test-token" };
const at = Date.parse("2026-10-24T02:11:00Z");

test("no public trigger endpoint", async () => {
  assert.equal((await worker.fetch()).status, 404);
});
test("missing secret fails closed", async () => {
  await assert.rejects(tick({}, at), /Missing/);
});
test("nighttime makes no API requests", async () => {
  assert.equal((await tick(env, Date.parse("2026-10-24T18:00:00Z"), () => assert.fail())).result, "outside_window");
});
test("running catch-up suppresses duplicate dispatch", async () => {
  let count = 0;
  const result = await tick(env, at, async () => {
    count++;
    return Response.json({ workflow_runs: [{ status: "in_progress" }] });
  });
  assert.equal(result.result, "already_active");
  assert.equal(count, 1);
});
test("only fixed repository workflow and main branch can be dispatched", async () => {
  const calls = [];
  const result = await tick(env, at, async (url, options) => {
    calls.push({ url, options });
    assert.ok(url.startsWith("https://api.github.com/repos/zer0err/tech-research-digest/actions/workflows/catchup.yml/"));
    assert.ok(!url.includes(env.GITHUB_DISPATCH_TOKEN));
    assert.equal(options.headers.Authorization, "Bearer fake-test-token");
    assert.equal(options.redirect, "error");
    return options.method === "POST" ? new Response(null, { status: 204 }) : Response.json({ workflow_runs: [] });
  });
  assert.equal(result.result, "dispatched");
  assert.equal(calls.length, 2);
  assert.deepEqual(JSON.parse(calls[1].options.body), { ref: "main" });
});
test("expired token errors contain no token", async () => {
  await assert.rejects(tick(env, at, async () => new Response("private details", { status: 401 })),
    error => error.message === "GitHub API HTTP 401" && !error.message.includes(env.GITHUB_DISPATCH_TOKEN));
});
test("bad run data is not treated as permission to dispatch", async () => {
  await assert.rejects(tick(env, at, async () => Response.json({ message: "unexpected" })), /Invalid/);
});
