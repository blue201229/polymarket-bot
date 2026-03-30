"use client";
import { AIDecisionPanel } from "@/components/ai/AIDecisionPanel";
import { ParameterSuggestionsPanel } from "@/components/ai/ParameterSuggestionsPanel";
import { useQuery } from "@tanstack/react-query";
import { aiApi } from "@/lib/api";

export default function AIPage() {
  const { data: aiStatus } = useQuery({
    queryKey: ["ai-status"],
    queryFn: () => aiApi.status().then((r) => r.data),
  });

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-white">AI Center</h1>
        <p className="text-gray-400 text-sm mt-1">
          Monitor AI decisions, manage parameters, and review performance
        </p>
      </div>

      {/* AI Principles notice */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {[
          {
            icon: "🛡️",
            title: "Risk Engine is Final",
            desc: "AI suggestions never override deterministic risk rules",
          },
          {
            icon: "📋",
            title: "All Decisions Logged",
            desc: "Every AI call is recorded with input, output, and latency",
          },
          {
            icon: "🔧",
            title: "Human Approval Required",
            desc: "Parameter changes require explicit operator action",
          },
        ].map(({ icon, title, desc }) => (
          <div
            key={title}
            className="p-3 bg-gray-900/50 border border-gray-800 rounded-lg"
          >
            <div className="flex items-center gap-2 mb-1">
              <span>{icon}</span>
              <span className="text-white text-sm font-medium">{title}</span>
            </div>
            <p className="text-gray-400 text-xs">{desc}</p>
          </div>
        ))}
      </div>

      {/* Provider info */}
      {aiStatus && (
        <div className="flex items-center gap-4 p-4 bg-gray-900/50 border border-gray-800 rounded-xl">
          <div className="flex items-center gap-2">
            <span
              className={`w-2 h-2 rounded-full ${
                aiStatus.available ? "bg-emerald-400 animate-pulse" : "bg-red-400"
              }`}
            />
            <span className="text-white text-sm font-medium">
              {aiStatus.available ? "AI Active" : "AI Unavailable"}
            </span>
          </div>
          <div className="h-4 w-px bg-gray-700" />
          <span className="text-gray-400 text-sm">
            Provider: <span className="text-white">{aiStatus.provider}</span>
          </span>
          <span className="text-gray-400 text-sm">
            Model: <span className="text-white">{aiStatus.model}</span>
          </span>
          <span className="text-gray-400 text-sm">
            Timeout: <span className="text-white">{aiStatus.timeout_seconds}s</span>
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AIDecisionPanel />
        <ParameterSuggestionsPanel />
      </div>
    </div>
  );
}
