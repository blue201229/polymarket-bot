"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { walletsApi, type Wallet } from "@/lib/api";
import { useState } from "react";

export default function WalletsPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);
  const [newAddress, setNewAddress] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [copyEnabled, setCopyEnabled] = useState(false);

  const { data: wallets, isLoading } = useQuery({
    queryKey: ["wallets"],
    queryFn: () => walletsApi.list({ tracked_only: true }).then((r) => r.data),
    refetchInterval: 30000,
  });

  const addWallet = useMutation({
    mutationFn: (data: Record<string, unknown>) => walletsApi.add(data).then((r) => r.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wallets"] });
      setShowAdd(false);
      setNewAddress("");
      setNewLabel("");
      setCopyEnabled(false);
    },
  });

  const handleAdd = () => {
    if (!newAddress.trim()) return;
    addWallet.mutate({
      address: newAddress.trim(),
      label: newLabel || undefined,
      copy_trade_enabled: copyEnabled,
    });
  };

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Wallets</h1>
          <p className="text-gray-400 text-sm mt-1">Tracked wallets with AI quality analysis</p>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm rounded-lg"
        >
          + Add Wallet
        </button>
      </div>

      {/* Add wallet form */}
      {showAdd && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4 space-y-3">
          <h3 className="text-white font-medium">Add Wallet to Track</h3>
          <input
            type="text"
            placeholder="0x... wallet address"
            value={newAddress}
            onChange={(e) => setNewAddress(e.target.value)}
            className="w-full bg-gray-800 text-white text-sm px-3 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-purple-500 font-mono"
          />
          <input
            type="text"
            placeholder="Label (optional)"
            value={newLabel}
            onChange={(e) => setNewLabel(e.target.value)}
            className="w-full bg-gray-800 text-white text-sm px-3 py-2 rounded-lg border border-gray-700 focus:outline-none focus:border-purple-500"
          />
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={copyEnabled}
              onChange={(e) => setCopyEnabled(e.target.checked)}
              className="rounded"
            />
            <span className="text-gray-300 text-sm">Enable copy trading</span>
            <span className="text-gray-500 text-xs">(requires AI quality score ≥ 6.5)</span>
          </label>
          <div className="flex gap-2">
            <button
              onClick={handleAdd}
              disabled={addWallet.isPending}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm rounded-lg"
            >
              {addWallet.isPending ? "Adding..." : "Add Wallet"}
            </button>
            <button
              onClick={() => setShowAdd(false)}
              className="px-4 py-2 bg-gray-700 text-white text-sm rounded-lg"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Wallet grid */}
      {isLoading ? (
        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-32 bg-gray-700/30 rounded-xl animate-pulse" />
          ))}
        </div>
      ) : !wallets?.length ? (
        <div className="text-center py-16 text-gray-500">
          <p className="text-lg mb-2">No wallets tracked</p>
          <p className="text-sm">Add a wallet address to start monitoring and AI analysis.</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {(wallets as Wallet[]).map((wallet) => (
            <WalletCard key={wallet.id} wallet={wallet} />
          ))}
        </div>
      )}
    </div>
  );
}

function WalletCard({ wallet }: { wallet: Wallet }) {
  const score = wallet.ai_quality_score;
  const scoreColor =
    score == null ? "text-gray-500" :
    score >= 7 ? "text-emerald-400" :
    score >= 5 ? "text-yellow-400" : "text-red-400";

  return (
    <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-4">
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <code className="text-gray-200 text-sm">
              {wallet.address.slice(0, 8)}...{wallet.address.slice(-6)}
            </code>
            {wallet.label && <span className="text-gray-400 text-xs">{wallet.label}</span>}
            {wallet.copy_trade_enabled && (
              <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded text-xs">
                Copy Trade
              </span>
            )}
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span>Trades: <span className="text-white">{wallet.total_trades}</span></span>
            {wallet.win_rate != null && (
              <span>Win Rate: <span className="text-white">{(wallet.win_rate * 100).toFixed(1)}%</span></span>
            )}
            <span>Volume: <span className="text-white">${(wallet.total_volume_usdc / 1000).toFixed(1)}K</span></span>
          </div>

          {/* AI Analysis */}
          {wallet.ai_quality_score != null && (
            <div className="mt-2 p-2.5 bg-gray-800/40 rounded-lg">
              <div className="flex items-center gap-3 mb-1">
                <span className="text-gray-400 text-xs">🤖 AI Analysis</span>
                <span className={`font-bold text-sm ${scoreColor}`}>
                  {wallet.ai_quality_score.toFixed(1)}/10
                </span>
                {wallet.ai_strategy_class && (
                  <span className="px-1.5 py-0.5 bg-gray-700 rounded text-xs text-gray-300">
                    {wallet.ai_strategy_class}
                  </span>
                )}
                {wallet.ai_confidence != null && (
                  <span className="text-gray-500 text-xs">
                    conf: {(wallet.ai_confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {wallet.ai_analysis_summary && (
                <p className="text-gray-400 text-xs">{wallet.ai_analysis_summary}</p>
              )}
            </div>
          )}
        </div>

        {/* Score circle */}
        <div className={`text-2xl font-bold flex-shrink-0 ${scoreColor}`}>
          {score != null ? score.toFixed(1) : "?"}
        </div>
      </div>
    </div>
  );
}
