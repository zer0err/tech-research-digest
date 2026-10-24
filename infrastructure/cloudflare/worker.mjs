// Independent clock only. Collection, model calls and publication stay in GitHub Actions.
const ACTIVE = new Set(["queued", "in_progress", "waiting", "pending", "requested"]);
const RETRYABLE = new Set([429, 500, 502, 503, 504]);

async function github(path, env, options = {}, request = fetch) {
  for (let attempt = 0; attempt < 3; attempt++) {
    const response = await request(`https://api.github.com/repos/zer0err/tech-research-digest${path}`, {
      ...options,
      redirect: "error",
      signal: AbortSignal.timeout(15000),
      headers: {
        "Authorization": `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Vorasio-Independent-Scheduler",
        "X-GitHub-Api-Version": "2022-11-28",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
      },
    });
    if (response.ok) return response;
    if (!RETRYABLE.has(response.status) || attempt === 2) {
      // Never log tokens, headers or raw upstream response bodies.
      throw new Error(`GitHub API HTTP ${response.status}`);
    }
    const retryAfter = Number(response.headers.get("retry-after"));
    await response.body?.cancel();
    await new Promise(resolve => setTimeout(resolve,
      Math.min(30000, retryAfter > 0 ? retryAfter * 1000 : 1000 * 2 ** attempt)));
  }
}

export async function tick(env, at = Date.now(), request = fetch) {
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error("Missing GITHUB_DISPATCH_TOKEN secret");
  const localHour = new Date(at + 8 * 3600000).getUTCHours();
  if (localHour < 9 || localHour > 23) return { result: "outside_window" };
  const response = await github("/actions/workflows/catchup.yml/runs?per_page=10", env, {}, request);
  const data = await response.json();
  if (!Array.isArray(data.workflow_runs)) throw new Error("Invalid GitHub workflow response");
  if (data.workflow_runs.some(run => ACTIVE.has(run.status))) return { result: "already_active" };
  await github("/actions/workflows/catchup.yml/dispatches", env,
    { method: "POST", body: JSON.stringify({ ref: "main" }) }, request);
  return { result: "dispatched" };
}

export default {
  async scheduled(event, env) {
    const result = await tick(env, event.scheduledTime);
    console.log(JSON.stringify({ ...result, scheduled_at: new Date(event.scheduledTime).toISOString() }));
  },
  async fetch() {
    return new Response("Not found", { status: 404 });
  },
};
