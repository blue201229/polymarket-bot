"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { systemApi, type RiskParams } from "@/lib/api";
import { useState } from "react";

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const { data: risk, isLoading } = useQuery({
    queryKey: ["risk"],
    queryFn: () => systemApi.risk().then((r) => r.data),
  });

  const { data: health } = useQuery({
    queryKey: ["health"],
    queryFn: () => systemApi.health().then((r) => r.data),
  });

  const updateRisk = useMutation({
    mutationFn: (data: Partial<RiskParams>) => systemApi.updateRisk(data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["risk"] });
      setFeedback({ type: "success", msg: "Risk parameters updated successfully." });
      setTimeout(() => setFeedback(null), 3000);
    },
    onError: () => setFeedback({ type: "error", msg: "Failed to update parameters." }),
  });

  const pauseTrading = useMutation({
    mutationFn: () => systemApi.pause("operator_request"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["risk"] }),
  });

  const resumeTrading = useMutation({
    mutationFn: () => systemApi.resume(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["risk"] }),
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-700 rounded w-1/4" />
          <div className="h-64 bg-gray-700/50 rounded-xl" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 text-sm mt-1">Risk engine configuration and trading controls</p>
      </div>

      {feedback && (
        <div
          className={`px-4 py-3 rounded-lg text-sm ${
            feedback.type === "success"
              ? "bg-green-500/10 border border-green-500/20 text-green-300"
              : "bg-red-500/10 border border-red-500/20 text-red-300"
          }`}
        >
          {feedback.msg}
        </div>
      )}

      {/* Trading Controls */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
        <h2 className="text-white font-semibold mb-4">Trading Controls</h2>
        <div className="flex items-center gap-4">
          <div>
            <p className="text-gray-200 text-sm">
              Status:{" "}
              <span
                className={`font-medium ${
                  risk?.trading_paused ? "text-red-400" : "text-emerald-400"
                }`}
              >
                {risk?.trading_paused ? "⏸️ PAUSED" : "▶️ Active"}
              </span>
            </p>
            {risk?.pause_reason && (
              <p className="text-gray-500 text-xs mt-0.5">Reason: {risk.pause_reason}</p>
            )}
          </div>
          {risk?.trading_paused ? (
            <button
              onClick={() => resumeTrading.mutate()}
              disabled={resumeTrading.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm rounded-lg"
            >
              Resume Trading
            </button>
          ) : (
            <button
              onClick={() => pauseTrading.mutate()}
              disabled={pauseTrading.isPending}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white text-sm rounded-lg"
            >
              Pause Trading
            </button>
          )}
        </div>
      </div>

      {/* Risk Parameters */}
      <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
        <h2 className="text-white font-semibold mb-1">Risk Parameters</h2>
        <p className="text-gray-500 text-xs mb-4">
          ⚠️ These are hard limits. AI cannot override these values.
        </p>

        <div className="space-y-4">
          <RiskField
            label="Max Position Size (USDC)"
            value={risk?.max_position_size_usdc}
            onSave={(v) => updateRisk.mutate({ max_position_size_usdc: v })}
            min={10}
            max={500}
            step={10}
          />
          <RiskField
            label="Max Total Exposure (USDC)"
            value={risk?.max_total_exposure_usdc}
            onSave={(v) => updateRisk.mutate({ max_total_exposure_usdc: v })}
            min={100}
            max={10000}
            step={100}
          />
          <RiskField
            label="Max Positions"
            value={risk?.max_positions}
            onSave={(v) => updateRisk.mutate({ max_positions: v })}
            min={1}
            max={50}
            step={1}
          />
          <RiskField
            label="Max Spread %"
            value={risk ? risk.max_spread_pct * 100 : undefined}
            onSave={(v) => updateRisk.mutate({ max_spread_pct: v / 100 })}
            min={0.5}
            max={20}
            step={0.5}
            format={(v) => `${v.toFixed(1)}%`}
          />
          <RiskField
            label="Max Slippage %"
            value={risk ? risk.max_slippage_pct * 100 : undefined}
            onSave={(v) => updateRisk.mutate({ max_slippage_pct: v / 100 })}
            min={0.1}
            max={10}
            step={0.1}
            format={(v) => `${v.toFixed(1)}%`}
          />
        </div>
      </div>

      {/* System info */}
      {health && (
        <div className="bg-gray-900/50 rounded-xl border border-gray-800 p-4">
          <h2 className="text-white font-semibold mb-3">System Info</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <span className="text-gray-500">Version:</span>{" "}
              <span className="text-white">{health.version}</span>
            </div>
            <div>
              <span className="text-gray-500">Mode:</span>{" "}
              <span className="text-white">{health.paper_trading ? "Paper" : "Live"}</span>
            </div>
            <div>
              <span className="text-gray-500">AI Enabled:</span>{" "}
              <span className={health.ai_enabled ? "text-emerald-400" : "text-gray-400"}>
                {health.ai_enabled ? "Yes" : "No"}
              </span>
            </div>
            <div>
              <span className="text-gray-500">AI Available:</span>{" "}
              <span className={health.ai_available ? "text-emerald-400" : "text-red-400"}>
                {health.ai_available ? "Yes" : "No"}
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function RiskField({
  label,
  value,
  onSave,
  min,
  max,
  step,
  format,
}: {
  label: string;
  value?: number;
  onSave: (v: number) => void;
  min: number;
  max: number;
  step: number;
  format?: (v: number) => string;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(String(value ?? ""));

  const display = value != null ? (format ? format(value) : String(value)) : "—";

  const handleSave = () => {
    const parsed = parseFloat(draft);
    if (!isNaN(parsed) && parsed >= min && parsed <= max) {
      onSave(parsed);
      setEditing(false);
    }
  };

  return (
    <div className="flex items-center justify-between">
      <div>
        <p className="text-gray-200 text-sm">{label}</p>
        <p className="text-gray-500 text-xs">
          Range: {format ? format(min) : min} – {format ? format(max) : max}
        </p>
      </div>
      {editing ? (
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            min={min}
            max={max}
            step={step}
            className="w-24 bg-gray-800 text-white text-sm px-2 py-1 rounded border border-gray-600 focus:outline-none focus:border-purple-500"
          />
          <button onClick={handleSave} className="px-2 py-1 bg-emerald-600 text-white text-xs rounded">
            Save
          </button>
          <button onClick={() => setEditing(false)} className="px-2 py-1 bg-gray-700 text-white text-xs rounded">
            Cancel
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-3">
          <span className="text-white font-mono text-sm">{display}</span>
          <button
            onClick={() => { setDraft(String(value ?? "")); setEditing(true); }}
            className="text-xs text-gray-400 hover:text-white underline"
          >
            Edit
          </button>
        </div>
      )}
    </div>
  );
}
