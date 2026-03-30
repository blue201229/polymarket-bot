"use client";
import { useQuery } from "@tanstack/react-query";
import { aiApi, type AILog } from "@/lib/api";
import { formatDistanceToNow } from "date-fns";

export function AIDecisionPanel() {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["ai-logs"],
    queryFn: () => aiApi.logs({ limit: 20 }).then((r) => r.data),
    refetchInterval: 15000,
  });

  const { data: aiStatus } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status().then((r) => r.data),
    refetchInterval: 30000,
  });

  if (isLoading) {
    return (
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4 animate-pulse">
        <div className="h-4 bg-gray-700 rounded w-1/3 mb-4" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-gray-700/50 rounded" />
          ))}
        </div>
      </div>
    );
  }

  const available = aiStatus?.available;

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <span className="text-white font-semibold">🤖 AI Decision Log</span>
          <span
            className={`px-2 py-0.5 rounded-full text-xs font-medium ${
              available
                ? "bg-emerald-500/20 text-emerald-300"
                : "bg-red-500/20 text-red-300"
            }`}
          >
            {available ? "Active" : "Unavailable"}
          </span>
        </div>
        {aiStatus && (
          <span className="text-xs text-gray-500">
            {aiStatus.provider} / {aiStatus.model?.split("-").slice(0, 3).join("-")}
          </span>
        )}
      </div>

      {/* Notice */}
      <div className="mb-3 px-3 py-2 bg-blue-500/10 border border-blue-500/20 rounded-lg">
        <p className="text-xs text-blue-300">
          ℹ️ AI provides advisory signals only. Risk engine rules are always final.
          AI can be disabled in system settings.
        </p>
      </div>

      {/* Logs */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {!logs || logs.length === 0 ? (
          <p className="text-gray-500 text-sm text-center py-8">
            No AI decisions recorded yet.
          </p>
        ) : (
          (logs as AILog[]).map((log) => (
            <AILogRow key={log.id} log={log} />
          ))
        )}
      </div>
    </div>
  );
}

function AILogRow({ log }: { log: AILog }) {
  const output = log.output_parsed as Record<string, unknown> | undefined;
  const score = output?.score as number | undefined;
  const confidence = output?.confidence as number | undefined;
  const decision = output?.decision as string | undefined;
  const action = output?.recommended_action as string | undefined;

  const primaryValue = score ?? confidence;
  const primaryLabel = score !== undefined ? "score" : confidence !== undefined ? "conf." : null;
  const secondaryValue = decision ?? action;

  return (
    <div className="flex items-start gap-3 p-2.5 rounded-lg bg-gray-800/40 hover:bg-gray-800/60 transition-colors">
      {/* Status indicator */}
      <div className={`mt-0.5 w-2 h-2 rounded-full flex-shrink-0 ${log.success ? "bg-emerald-400" : "bg-red-400"}`} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-gray-200 text-xs font-medium">{log.component}</span>
          {log.cache_hit && (
            <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs">cached</span>
          )}
        </div>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-gray-500 text-xs">{log.latency_ms.toFixed(0)}ms</span>
          {primaryValue !== undefined && primaryLabel && (
            <span className="text-gray-400 text-xs">
              {primaryLabel}: <span className="text-white">{typeof primaryValue === "number" ? primaryValue.toFixed(2) : primaryValue}</span>
            </span>
          )}
          {secondaryValue && (
            <span className={`text-xs font-medium ${
              secondaryValue === "execute" || secondaryValue === "trade"
                ? "text-emerald-400"
                : secondaryValue === "skip" || secondaryValue === "avoid"
                ? "text-red-400"
                : "text-yellow-400"
            }`}>
              → {secondaryValue}
            </span>
          )}
        </div>
      </div>

      <span className="text-gray-600 text-xs flex-shrink-0">
        {formatDistanceToNow(new Date(log.created_at), { addSuffix: true })}
      </span>
    </div>
  );
}
