"use client";
import { useQuery } from "@tanstack/react-query";
import { marketsApi, tradesApi, aiApi, systemApi } from "@/lib/api";
import { AIScoreBadge } from "@/components/ai/AIScoreBadge";

export default function DashboardPage() {
  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => systemApi.health().then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: tradeStats } = useQuery({
    queryKey: ["trade-stats"],
    queryFn: () => tradesApi.stats().then((r) => r.data),
    refetchInterval: 30000,
  });

  const { data: topMarkets } = useQuery({
    queryKey: ["top-markets"],
    queryFn: () => marketsApi.list({ limit: 5, min_score: 7 }).then((r) => r.data),
    refetchInterval: 60000,
  });

  const { data: aiStatus } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status().then((r) => r.data),
    refetchInterval: 60000,
  });

  const paperMode = health?.paper_trading ?? true;

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 text-sm mt-1">
          AI-assisted prediction market trading platform
        </p>
      </div>

      {/* Status strip */}
      {paperMode && (
        <div className="flex items-center gap-2 px-4 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg">
          <span className="text-blue-300 text-sm">📝</span>
          <span className="text-blue-300 text-sm font-medium">Paper Trading Mode Active</span>
          <span className="text-blue-400/70 text-sm">— No real funds at risk</span>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Trades"
          value={String(tradeStats?.total_trades ?? "—")}
          sub="all time"
          icon="📊"
        />
        <StatCard
          label="Win Rate"
          value={tradeStats?.win_rate != null ? `${(tradeStats.win_rate * 100).toFixed(1)}%` : "—"}
          sub="filled trades"
          icon="🎯"
          positive={tradeStats?.win_rate != null && tradeStats.win_rate > 0.5}
        />
        <StatCard
          label="Total PnL"
          value={tradeStats?.total_pnl_usdc != null ? `$${tradeStats.total_pnl_usdc.toFixed(2)}` : "—"}
          sub="paper USDC"
          icon="💰"
          positive={tradeStats?.total_pnl_usdc != null && tradeStats.total_pnl_usdc > 0}
        />
        <StatCard
          label="AI Engine"
          value={aiStatus?.available ? "Active" : "Unavailable"}
          sub={aiStatus?.model?.split("-").slice(0, 3).join("-") ?? "not configured"}
          icon="🤖"
          positive={aiStatus?.available}
        />
      </div>

      {/* Top markets */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
        <h2 className="text-white font-semibold mb-4">
          🏆 Top AI-Scored Markets
          <span className="ml-2 text-xs text-gray-500 font-normal">(score ≥ 7.0)</span>
        </h2>

        {!topMarkets?.markets?.length ? (
          <p className="text-gray-500 text-sm py-4 text-center">
            No high-scored markets yet. Run market discovery to populate.
          </p>
        ) : (
          <div className="space-y-3">
            {topMarkets.markets.map((market) => {
              let tags: string[] = [];
              try {
                tags = market.ai_tags ? JSON.parse(market.ai_tags) : [];
              } catch { tags = []; }

              return (
                <div
                  key={market.id}
                  className="flex items-start gap-4 p-3 bg-gray-800/40 rounded-lg hover:bg-gray-800/60 transition-colors"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-200 text-sm line-clamp-2">{market.question}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                      <span>Bid: {market.best_bid?.toFixed(3) ?? "—"}</span>
                      <span>Ask: {market.best_ask?.toFixed(3) ?? "—"}</span>
                      <span>Liq: ${(market.liquidity / 1000).toFixed(0)}K</span>
                    </div>
                  </div>
                  <AIScoreBadge
                    score={market.ai_score}
                    reasoning={market.ai_reasoning}
                    tags={tags}
                    size="lg"
                  />
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* AI disclaimer */}
      <div className="px-4 py-3 bg-gray-900/50 border border-gray-800 rounded-lg">
        <p className="text-gray-500 text-xs">
          🤖 <strong className="text-gray-400">AI Disclaimer:</strong> AI scores and signals are advisory only.
          Deterministic risk rules always have final authority. AI decisions are fully logged and auditable.
          AI can be disabled at any time via system settings.
        </p>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  sub,
  icon,
  positive,
}: {
  label: string;
  value: string;
  sub: string;
  icon: string;
  positive?: boolean;
}) {
  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center gap-2 mb-2">
        <span>{icon}</span>
        <span className="text-gray-400 text-xs">{label}</span>
      </div>
      <p
        className={`text-2xl font-bold ${
          positive === undefined
            ? "text-white"
            : positive
            ? "text-emerald-400"
            : "text-red-400"
        }`}
      >
        {value}
      </p>
      <p className="text-gray-600 text-xs mt-1">{sub}</p>
    </div>
  );
}
