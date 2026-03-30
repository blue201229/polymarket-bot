"use client";
import { useQuery } from "@tanstack/react-query";
import { aiApi, systemApi } from "@/lib/api";

export function ParameterSuggestionsPanel() {
  const { data: optimizations, isLoading, refetch } = useQuery({
    queryKey: ["ai-optimizations"],
    queryFn: () => aiApi.optimize().then((r) => r.data),
    enabled: false, // Manual trigger only
  });

  const handleApplySuggestion = async (param: string, value: unknown) => {
    if (!confirm(`Apply suggested change: ${param} = ${value}?\nThis requires manual confirmation.`)) {
      return;
    }
    try {
      await systemApi.updateRisk({ [param]: value } as Record<string, unknown>);
      alert("Parameter updated successfully.");
    } catch {
      alert("Failed to apply parameter change.");
    }
  };

  return (
    <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-white font-semibold">⚙️ AI Parameter Suggestions</h3>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          className="px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white text-xs rounded-lg transition-colors"
        >
          {isLoading ? "Analyzing..." : "Run Analysis"}
        </button>
      </div>

      {/* Critical notice */}
      <div className="mb-4 px-3 py-2 bg-orange-500/10 border border-orange-500/20 rounded-lg">
        <p className="text-xs text-orange-300">
          ⚠️ <strong>AI suggestions require manual approval.</strong> Changes are never auto-applied.
          Review each suggestion carefully before applying.
        </p>
      </div>

      {!optimizations ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-sm">Click &quot;Run Analysis&quot; to generate AI parameter suggestions based on recent performance.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {/* Overall assessment */}
          <div className="p-3 bg-gray-800/40 rounded-lg">
            <p className="text-xs text-gray-400 mb-1">Overall Assessment</p>
            <p className="text-gray-200 text-sm">{optimizations.overall_assessment}</p>
            <span className={`mt-2 inline-block px-2 py-0.5 rounded text-xs font-medium ${
              optimizations.priority === "high"
                ? "bg-red-500/20 text-red-300"
                : optimizations.priority === "medium"
                ? "bg-yellow-500/20 text-yellow-300"
                : "bg-gray-700 text-gray-400"
            }`}>
              Priority: {optimizations.priority}
            </span>
          </div>

          {/* Suggestions */}
          {optimizations.suggestions?.length === 0 ? (
            <p className="text-gray-500 text-sm text-center py-4">No changes suggested at this time.</p>
          ) : (
            optimizations.suggestions?.map((suggestion: Record<string, unknown>, i: number) => (
              <SuggestionCard
                key={i}
                suggestion={suggestion}
                onApply={() => handleApplySuggestion(suggestion.parameter as string, suggestion.suggested_value)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}

function SuggestionCard({
  suggestion,
  onApply,
}: {
  suggestion: Record<string, unknown>;
  onApply: () => void;
}) {
  const changePct = suggestion.change_pct as number;
  const isIncrease = changePct > 0;

  return (
    <div className="p-3 bg-gray-800/40 border border-gray-700/50 rounded-lg">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <code className="text-yellow-300 text-xs bg-gray-700/50 px-1.5 py-0.5 rounded">
              {suggestion.parameter as string}
            </code>
            <span className={`text-xs font-medium ${isIncrease ? "text-emerald-400" : "text-red-400"}`}>
              {isIncrease ? "▲" : "▼"} {Math.abs(changePct).toFixed(1)}%
            </span>
            <span className="text-xs text-gray-500">
              confidence: {((suggestion.confidence as number) * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <span>Current: <span className="text-white">{String(suggestion.current_value)}</span></span>
            <span>→</span>
            <span>Suggested: <span className="text-white">{String(suggestion.suggested_value)}</span></span>
          </div>
          <p className="text-gray-300 text-xs">{suggestion.rationale as string}</p>
          <p className="text-gray-500 text-xs mt-1">Expected: {suggestion.expected_impact as string}</p>
        </div>
        <button
          onClick={onApply}
          className="flex-shrink-0 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs rounded-lg transition-colors"
        >
          Apply
        </button>
      </div>
    </div>
  );
}
