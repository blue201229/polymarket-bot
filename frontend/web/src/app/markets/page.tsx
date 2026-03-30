"use client";
import { MarketTable } from "@/components/markets/MarketTable";
import { marketsApi } from "@/lib/api";
import { useState } from "react";

export default function MarketsPage() {
  const [discovering, setDiscovering] = useState(false);
  const [discoverResult, setDiscoverResult] = useState<Record<string, unknown> | null>(null);

  const handleDiscover = async () => {
    setDiscovering(true);
    try {
      const result = await marketsApi.discover({ limit: 200, min_volume: 500 });
      setDiscoverResult(result.data);
    } catch (e) {
      console.error("Discovery failed:", e);
    } finally {
      setDiscovering(false);
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Markets</h1>
          <p className="text-gray-400 text-sm mt-1">
            All tracked markets with AI quality scores
          </p>
        </div>
        <button
          onClick={handleDiscover}
          disabled={discovering}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-sm rounded-lg transition-colors"
        >
          {discovering ? "Discovering..." : "🔍 Discover Markets"}
        </button>
      </div>

      {discoverResult && (
        <div className="px-4 py-3 bg-green-500/10 border border-green-500/20 rounded-lg text-sm text-green-300">
          ✅ Discovery complete: {String(discoverResult.fetched ?? 0)} fetched,{" "}
          {String(discoverResult.after_filter ?? 0)} passed filters,{" "}
          {String(discoverResult.saved ?? 0)} saved.
          {discoverResult.ai_scoring_queued && " AI scoring queued."}
        </div>
      )}

      <MarketTable showAIScores />
    </div>
  );
}
