"use client";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { marketsApi, type Market } from "@/lib/api";
import { AIScoreBadge } from "@/components/ai/AIScoreBadge";
import { formatDistanceToNow } from "date-fns";

interface MarketTableProps {
  showAIScores?: boolean;
}

export function MarketTable({ showAIScores = true }: MarketTableProps) {
  const [page, setPage] = useState(1);
  const [minScore, setMinScore] = useState(0);
  const [showAI, setShowAI] = useState(showAIScores);

  const { data, isLoading } = useQuery({
    queryKey: ["markets", page, minScore],
    queryFn: () =>
      marketsApi.list({ page, limit: 20, min_score: minScore }).then((r) => r.data),
    refetchInterval: 30000,
  });

  const handleScoreMarket = async (conditionId: string) => {
    try {
      await marketsApi.score(conditionId);
    } catch (e) {
      console.error("Score request failed:", e);
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-gray-400 text-sm">Min AI Score:</label>
          <select
            value={minScore}
            onChange={(e) => { setMinScore(Number(e.target.value)); setPage(1); }}
            className="bg-gray-800 text-white text-sm rounded-lg px-2 py-1 border border-gray-700"
          >
            <option value={0}>All</option>
            <option value={5}>5+</option>
            <option value={7}>7+</option>
            <option value={8}>8+</option>
          </select>
        </div>

        {/* AI vs Non-AI toggle */}
        <div className="flex items-center gap-2">
          <label className="text-gray-400 text-sm">AI Scores:</label>
          <button
            onClick={() => setShowAI(!showAI)}
            className={`relative inline-flex h-5 w-9 rounded-full transition-colors ${
              showAI ? "bg-purple-600" : "bg-gray-700"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 mt-0.5 rounded-full bg-white shadow transition-transform ${
                showAI ? "translate-x-4" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                <th className="text-left text-gray-400 text-xs font-medium px-4 py-3">Market</th>
                <th className="text-right text-gray-400 text-xs font-medium px-4 py-3">Price</th>
                <th className="text-right text-gray-400 text-xs font-medium px-4 py-3">Spread</th>
                <th className="text-right text-gray-400 text-xs font-medium px-4 py-3">24h Vol</th>
                <th className="text-right text-gray-400 text-xs font-medium px-4 py-3">Liquidity</th>
                {showAI && (
                  <th className="text-right text-gray-400 text-xs font-medium px-4 py-3">
                    AI Score
                    <span className="ml-1 text-purple-400">🤖</span>
                  </th>
                )}
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td colSpan={7} className="px-4 py-3">
                      <div className="h-8 bg-gray-700/30 rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : (
                data?.markets.map((market) => (
                  <MarketRow
                    key={market.id}
                    market={market}
                    showAI={showAI}
                    onScoreRequest={() => handleScoreMarket(market.condition_id)}
                  />
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {data && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
            <span className="text-gray-500 text-xs">{data.total} total markets</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-white text-xs rounded-lg"
              >
                Previous
              </button>
              <span className="px-3 py-1 text-gray-400 text-xs">Page {page}</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={data.markets.length < 20}
                className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-white text-xs rounded-lg"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MarketRow({
  market,
  showAI,
  onScoreRequest,
}: {
  market: Market;
  showAI: boolean;
  onScoreRequest: () => void;
}) {
  let tags: string[] = [];
  if (market.ai_tags) {
    try {
      tags = JSON.parse(market.ai_tags);
    } catch {
      tags = [];
    }
  }

  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/20 transition-colors">
      <td className="px-4 py-3">
        <div className="max-w-xs">
          <p className="text-gray-200 text-sm line-clamp-2">{market.question}</p>
          {market.category && (
            <span className="text-gray-500 text-xs mt-0.5">{market.category}</span>
          )}
        </div>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-white text-sm font-mono">
          {market.mid_price ? `${(market.mid_price * 100).toFixed(1)}¢` : "—"}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <span className={`text-sm font-mono ${
          (market.spread_pct || 0) > 0.05 ? "text-red-400" : "text-gray-300"
        }`}>
          {market.spread_pct ? `${(market.spread_pct * 100).toFixed(2)}%` : "—"}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-gray-300 text-sm">
          ${market.volume_24h >= 1000
            ? `${(market.volume_24h / 1000).toFixed(1)}K`
            : market.volume_24h.toFixed(0)}
        </span>
      </td>
      <td className="px-4 py-3 text-right">
        <span className="text-gray-300 text-sm">
          ${market.liquidity >= 1000
            ? `${(market.liquidity / 1000).toFixed(1)}K`
            : market.liquidity.toFixed(0)}
        </span>
      </td>
      {showAI && (
        <td className="px-4 py-3 text-right">
          {market.ai_score !== null && market.ai_score !== undefined ? (
            <AIScoreBadge
              score={market.ai_score}
              reasoning={market.ai_reasoning}
              tags={tags}
            />
          ) : (
            <button
              onClick={onScoreRequest}
              className="text-xs text-purple-400 hover:text-purple-300 underline"
            >
              Score
            </button>
          )}
        </td>
      )}
      <td className="px-4 py-3">
        <div className="flex items-center gap-1">
          {!market.active && (
            <span className="px-1.5 py-0.5 bg-gray-700 rounded text-xs text-gray-400">Inactive</span>
          )}
          {market.closed && (
            <span className="px-1.5 py-0.5 bg-gray-700 rounded text-xs text-gray-400">Closed</span>
          )}
        </div>
      </td>
    </tr>
  );
}
