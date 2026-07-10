// 磐田ライフハック Worker本体。
// 静的アセット配信は env.ASSETS に委譲し、/api/search-log のみ自前処理する。
// Phase 0(計測基盤): 検索クエリと0件ヒットをWorkers Analytics Engineへ記録する。

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

async function handleSearchLog(request, env) {
  if (request.method === "OPTIONS") {
    return new Response(null, { status: 204, headers: corsHeaders() });
  }
  if (request.method !== "POST") {
    return new Response("Method Not Allowed", { status: 405, headers: corsHeaders() });
  }

  let body;
  try {
    body = await request.json();
  } catch (e) {
    return new Response("Bad Request", { status: 400, headers: corsHeaders() });
  }

  const query = String(body.query || "").slice(0, 100);
  const hits = Number.isFinite(body.hits) ? body.hits : -1;
  const path = String(body.path || "").slice(0, 200);

  if (!query) {
    return new Response("Bad Request", { status: 400, headers: corsHeaders() });
  }

  if (env.SEARCH_LOGS) {
    env.SEARCH_LOGS.writeDataPoint({
      blobs: [query, path],
      doubles: [hits],
      indexes: [hits === 0 ? "zero_hit" : "hit"],
    });
  }

  return new Response(null, { status: 204, headers: corsHeaders() });
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/api/search-log") {
      return handleSearchLog(request, env);
    }
    return env.ASSETS.fetch(request);
  },
};
