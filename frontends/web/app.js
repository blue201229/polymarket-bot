const DEFAULT_API_BASE = "http://localhost:8000";
const elements = {
  apiBase: document.getElementById("apiBase"),
  saveApiBase: document.getElementById("saveApiBase"),
  refreshBtn: document.getElementById("refreshBtn"),
  marketsBody: document.getElementById("marketsBody"),
  suggestionsBody: document.querySelector("#suggestionsTable tbody"),
  statusPill: document.getElementById("statusPill"),
};

elements.apiBase.value = localStorage.getItem("api_base") || DEFAULT_API_BASE;

function setStatus(text, cls = "") {
  elements.statusPill.textContent = text;
  elements.statusPill.className = `status-pill ${cls}`.trim();
}

function renderMarkets(markets) {
  elements.marketsBody.innerHTML = "";
  if (!markets.length) {
    elements.marketsBody.innerHTML = `<tr><td colspan="7" class="muted">No markets available</td></tr>`;
    return;
  }

  for (const market of markets) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${market.market_id}</td>
      <td>${market.question}</td>
      <td>${Number(market.volume_24h || 0).toFixed(0)}</td>
      <td>${Number(market.liquidity || 0).toFixed(0)}</td>
      <td>${Number(market.spread_bps || 0).toFixed(0)}</td>
      <td>${market.ai_score !== null && market.ai_score !== undefined ? Number(market.ai_score).toFixed(2) : "-"}</td>
      <td title="${market.ai_reasoning || "AI unavailable"}">${market.ai_reasoning || "N/A"}</td>
    `;
    elements.marketsBody.appendChild(row);
  }
}

function renderSuggestions(payload) {
  const suggestions = payload.suggestions || [];
  elements.suggestionsBody.innerHTML = "";
  if (!suggestions.length) {
    elements.suggestionsBody.innerHTML = `<tr><td colspan="3" class="muted">No suggestions yet.</td></tr>`;
    return;
  }

  for (const s of suggestions) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${s.parameter}</td>
      <td>${s.current_value} → ${s.suggested_value}</td>
      <td>${s.rationale}</td>
    `;
    elements.suggestionsBody.appendChild(row);
  }
}

async function fetchJson(path, options = undefined) {
  const base = elements.apiBase.value.trim().replace(/\/$/, "");
  const res = await fetch(`${base}${path}`, options);
  if (!res.ok) {
    throw new Error(`Request failed: ${res.status}`);
  }
  return res.json();
}

async function loadData() {
  setStatus("Loading...", "loading");
  try {
    const marketsResp = await fetchJson("/api/v1/markets");
    const markets = marketsResp.markets || [];

    const withAi = await Promise.all(
      markets.map(async (m) => {
        try {
          const ai = await fetchJson("/api/v1/ai/score-market", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(m),
          });
          return {
            ...m,
            ai_score: ai.score?.score ?? null,
            ai_reasoning: ai.score?.reasoning ?? null,
          };
        } catch {
          return { ...m, ai_score: null, ai_reasoning: "AI score unavailable." };
        }
      })
    );
    renderMarkets(withAi);

    const suggestions = await fetchJson("/api/v1/ai/optimize", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        recent_pnl: [1.2, -0.8, 0.4, -0.1],
        market_condition: "volatile",
      }),
    });
    renderSuggestions(suggestions);

    setStatus("Ready", "ok");
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  }
}

elements.refreshBtn.addEventListener("click", loadData);
elements.saveApiBase.addEventListener("click", () => {
  localStorage.setItem("api_base", elements.apiBase.value.trim());
  loadData();
});

loadData();
