import React from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  StyleSheet,
  SafeAreaView,
} from "react-native";
import { useQuery } from "@tanstack/react-query";
import { systemApi, marketsApi, tradesApi, aiApi } from "@/api/client";
import { AIScoreBadge } from "@/components/ai/AIScoreBadge";

export function DashboardScreen() {
  const { data: health, refetch: refetchHealth, isLoading } = useQuery({
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

  const onRefresh = () => {
    refetchHealth();
  };

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl refreshing={isLoading} onRefresh={onRefresh} tintColor="#A78BFA" />
        }
      >
        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.title}>Polymarket AI</Text>
          <Text style={styles.subtitle}>Trading Platform</Text>
        </View>

        {/* Paper trading banner */}
        {health?.paper_trading && (
          <View style={styles.paperBanner}>
            <Text style={styles.paperBannerText}>📝 Paper Trading Mode — No Real Funds</Text>
          </View>
        )}

        {/* AI status chip */}
        <View style={styles.aiStatusRow}>
          <View
            style={[
              styles.aiChip,
              { backgroundColor: aiStatus?.available ? "rgba(16,185,129,0.15)" : "rgba(239,68,68,0.15)" },
            ]}
          >
            <View
              style={[
                styles.aiDot,
                { backgroundColor: aiStatus?.available ? "#10B981" : "#EF4444" },
              ]}
            />
            <Text style={[styles.aiChipText, { color: aiStatus?.available ? "#6EE7B7" : "#FCA5A5" }]}>
              AI {aiStatus?.available ? "Active" : "Unavailable"}
            </Text>
          </View>
          {aiStatus?.model && (
            <Text style={styles.modelText}>
              {aiStatus.model.split("-").slice(0, 3).join("-")}
            </Text>
          )}
        </View>

        {/* Stats grid */}
        <View style={styles.statsGrid}>
          <StatCard label="Total Trades" value={String(tradeStats?.total_trades ?? "—")} icon="📊" />
          <StatCard
            label="Win Rate"
            value={tradeStats?.win_rate != null ? `${(tradeStats.win_rate * 100).toFixed(1)}%` : "—"}
            icon="🎯"
            positive={tradeStats?.win_rate != null && tradeStats.win_rate > 0.5}
          />
          <StatCard
            label="PnL"
            value={tradeStats?.total_pnl_usdc != null ? `$${Number(tradeStats.total_pnl_usdc).toFixed(2)}` : "—"}
            icon="💰"
            positive={tradeStats?.total_pnl_usdc != null && Number(tradeStats.total_pnl_usdc) > 0}
          />
          <StatCard
            label="Rejected"
            value={String(tradeStats?.risk_rejected ?? "—")}
            icon="🛡️"
          />
        </View>

        {/* Top markets */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>🏆 Top AI-Scored Markets</Text>
          {!topMarkets?.markets?.length ? (
            <Text style={styles.emptyText}>No scored markets yet. Run discovery.</Text>
          ) : (
            topMarkets.markets.map((market: Record<string, unknown>) => (
              <View key={market.id as string} style={styles.marketCard}>
                <View style={styles.marketCardContent}>
                  <Text style={styles.marketQuestion} numberOfLines={2}>
                    {market.question as string}
                  </Text>
                  <View style={styles.marketMeta}>
                    <Text style={styles.marketMetaText}>
                      ${(Number(market.liquidity) / 1000).toFixed(0)}K liq
                    </Text>
                    <Text style={styles.marketMetaText}>
                      {market.spread_pct != null ? `${(Number(market.spread_pct) * 100).toFixed(1)}% spread` : ""}
                    </Text>
                  </View>
                </View>
                <AIScoreBadge score={market.ai_score as number | undefined} size="lg" />
              </View>
            ))
          )}
        </View>

        {/* AI disclaimer */}
        <View style={styles.disclaimer}>
          <Text style={styles.disclaimerText}>
            🤖 AI scores are advisory only. Risk engine rules are always final.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

function StatCard({
  label,
  value,
  icon,
  positive,
}: {
  label: string;
  value: string;
  icon: string;
  positive?: boolean;
}) {
  const valueColor =
    positive === undefined ? "#F4F4F5" :
    positive ? "#34D399" : "#F87171";

  return (
    <View style={styles.statCard}>
      <Text style={styles.statIcon}>{icon}</Text>
      <Text style={[styles.statValue, { color: valueColor }]}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#09090B" },
  content: { padding: 16, gap: 16 },
  header: { paddingTop: 8 },
  title: { fontSize: 28, fontWeight: "800", color: "#F4F4F5" },
  subtitle: { fontSize: 14, color: "#71717A", marginTop: 2 },
  paperBanner: {
    backgroundColor: "rgba(59,130,246,0.1)",
    borderWidth: 1,
    borderColor: "rgba(59,130,246,0.2)",
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  paperBannerText: { color: "#93C5FD", fontSize: 13, fontWeight: "500" },
  aiStatusRow: { flexDirection: "row", alignItems: "center", gap: 8 },
  aiChip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 20,
  },
  aiDot: { width: 6, height: 6, borderRadius: 3 },
  aiChipText: { fontSize: 12, fontWeight: "600" },
  modelText: { fontSize: 11, color: "#52525B" },
  statsGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
  },
  statCard: {
    flex: 1,
    minWidth: "45%",
    backgroundColor: "rgba(24,24,27,0.8)",
    borderWidth: 1,
    borderColor: "#27272A",
    borderRadius: 12,
    padding: 14,
    gap: 4,
  },
  statIcon: { fontSize: 18 },
  statValue: { fontSize: 22, fontWeight: "800" },
  statLabel: { fontSize: 11, color: "#71717A" },
  section: {
    backgroundColor: "rgba(24,24,27,0.5)",
    borderWidth: 1,
    borderColor: "#27272A",
    borderRadius: 14,
    padding: 16,
    gap: 12,
  },
  sectionTitle: { fontSize: 16, fontWeight: "700", color: "#F4F4F5" },
  emptyText: { fontSize: 13, color: "#71717A", textAlign: "center", paddingVertical: 16 },
  marketCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    backgroundColor: "rgba(39,39,42,0.4)",
    borderRadius: 10,
    padding: 12,
  },
  marketCardContent: { flex: 1 },
  marketQuestion: { fontSize: 13, color: "#D4D4D8", fontWeight: "500", lineHeight: 18 },
  marketMeta: { flexDirection: "row", gap: 12, marginTop: 4 },
  marketMetaText: { fontSize: 11, color: "#71717A" },
  disclaimer: {
    backgroundColor: "rgba(24,24,27,0.5)",
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  disclaimerText: { fontSize: 11, color: "#52525B", lineHeight: 16 },
});
