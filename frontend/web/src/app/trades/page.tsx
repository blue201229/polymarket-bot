"use client";
import { useQuery } from "@tanstack/react-query";
import { tradesApi, type Trade } from "@/lib/api";
import { useState } from "react";
import { formatDistanceToNow } from "date-fns";

const STATUS_STYLE: Record<string, string> = {
  filled: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  risk_rejected: "bg-red-500/20 text-red-300 border-red-500/30",
  ai_skipped: "bg-purple-500/20 text-purple-300 border-purple-500/30",
  failed: "bg-red-700/20 text-red-400 border-red-700/30",
  pending: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
  submitted: "bg-blue-500/20 text-blue-300 border-blue-500/30",
};

export default function TradesPage() {
  const [page, setPage] = useState(1);
  const [statusFilter, setStatusFilter] = useState("");
  const [isPaperFilter, setIsPaperFilter] = useState<string>("all");

  const { data, isLoading } = useQuery({
    queryKey: ["trades", page, statusFilter, isPaperFilter],
    queryFn: () =>
      tradesApi.list({
        page,
        limit: 20,
        status: statusFilter || undefined,
        is_paper: isPaperFilter === "all" ? undefined : isPaperFilter === "paper",
      }).then((r) => r.data),
    refetchInterval: 10000,
  });

  const { data: stats } = useQuery({
    queryKey: ["trade-stats", isPaperFilter],
    queryFn: () =>
      tradesApi.stats({
        is_paper: isPaperFilter === "all" ? undefined : isPaperFilter === "paper",
      }).then((r) => r.data),
    refetchInterval: 15000,
  });

  return (
    <div className="p-6 space-y-6 max-w-7xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Trades</h1>
        <p className="text-gray-400 text-sm mt-1">Trade history with AI decisions</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            { label: "Filled", value: stats.filled ?? 0, color: "text-emerald-400" },
            { label: "Risk Rejected", value: stats.risk_rejected ?? 0, color: "text-red-400" },
            { label: "AI Skipped", value: stats.ai_skipped ?? 0, color: "text-purple-400" },
            { label: "Win Rate", value: stats.win_rate != null ? `${(stats.win_rate * 100).toFixed(1)}%` : "—", color: "text-white" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900/50 rounded-xl border border-gray-800 p-3">
              <p className="text-gray-400 text-xs">{label}</p>
              <p className={`text-xl font-bold mt-1 ${color}`}>{String(value)}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="bg-gray-800 text-white text-sm rounded-lg px-3 py-1.5 border border-gray-700"
        >
          <option value="">All Statuses</option>
          <option value="filled">Filled</option>
          <option value="risk_rejected">Risk Rejected</option>
          <option value="ai_skipped">AI Skipped</option>
          <option value="failed">Failed</option>
        </select>

        <select
          value={isPaperFilter}
          onChange={(e) => { setIsPaperFilter(e.target.value); setPage(1); }}
          className="bg-gray-800 text-white text-sm rounded-lg px-3 py-1.5 border border-gray-700"
        >
          <option value="all">All Modes</option>
          <option value="paper">Paper Only</option>
          <option value="live">Live Only</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-800">
                {["Market", "Side", "Size", "Price", "Status", "AI", "Time"].map((h) => (
                  <th key={h} className="text-left text-gray-400 text-xs font-medium px-4 py-3">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="border-b border-gray-800/50">
                    <td colSpan={7} className="px-4 py-3">
                      <div className="h-8 bg-gray-700/30 rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : (
                data?.trades.map((trade) => <TradeRow key={trade.id} trade={trade} />)
              )}
            </tbody>
          </table>
        </div>

        {data && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-800">
            <span className="text-gray-500 text-xs">{data.total} total trades</span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-white text-xs rounded"
              >
                Prev
              </button>
              <span className="px-3 py-1 text-gray-400 text-xs">Page {page}</span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={!data.trades.length || data.trades.length < 20}
                className="px-3 py-1 bg-gray-800 hover:bg-gray-700 disabled:opacity-40 text-white text-xs rounded"
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

function TradeRow({ trade }: { trade: Trade }) {
  const statusStyle = STATUS_STYLE[trade.status] || "bg-gray-700 text-gray-300";

  return (
    <tr className="border-b border-gray-800/50 hover:bg-gray-800/20">
      <td className="px-4 py-3">
        <div className="flex items-center gap-1.5">
          {trade.is_paper && (
            <span className="text-xs text-blue-400 border border-blue-400/30 px-1.5 py-0.5 rounded">Paper</span>
          )}
          <span className="text-gray-400 text-xs font-mono">{trade.condition_id.slice(0, 12)}…</span>
        </div>
        <span className="text-gray-500 text-xs">{trade.source}</span>
      </td>
      <td className="px-4 py-3">
        <span className={`text-sm font-medium ${trade.side === "buy" ? "text-emerald-400" : "text-red-400"}`}>
          {trade.side.toUpperCase()} {trade.outcome}
        </span>
      </td>
      <td className="px-4 py-3">
        <span className="text-white text-sm">${trade.size_usdc.toFixed(2)}</span>
      </td>
      <td className="px-4 py-3">
        <div>
          <span className="text-white text-sm font-mono">{trade.target_price.toFixed(4)}</span>
          {trade.executed_price && (
            <p className="text-gray-500 text-xs">exec: {trade.executed_price.toFixed(4)}</p>
          )}
        </div>
      </td>
      <td className="px-4 py-3">
        <span className={`px-2 py-0.5 rounded-full text-xs border ${statusStyle}`}>
          {trade.status.replace("_", " ")}
        </span>
        {trade.risk_rejection_reason && (
          <p className="text-red-400/70 text-xs mt-0.5">{trade.risk_rejection_reason.split(":")[0]}</p>
        )}
      </td>
      <td className="px-4 py-3">
        {trade.ai_confidence != null ? (
          <div>
            <div className="flex items-center gap-1">
              <span className="text-xs text-purple-300">{(trade.ai_confidence * 100).toFixed(0)}%</span>
              {trade.ai_decision && (
                <span className={`text-xs ${
                  trade.ai_decision === "execute" ? "text-emerald-400" : "text-red-400"
                }`}>
                  → {trade.ai_decision}
                </span>
              )}
            </div>
          </div>
        ) : (
          <span className="text-gray-600 text-xs">—</span>
        )}
      </td>
      <td className="px-4 py-3">
        <span className="text-gray-500 text-xs">
          {trade.created_at
            ? formatDistanceToNow(new Date(trade.created_at), { addSuffix: true })
            : "—"}
        </span>
      </td>
    </tr>
  );
}
