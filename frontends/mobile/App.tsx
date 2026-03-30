import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Switch,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

const API_BASE = process.env.EXPO_PUBLIC_API_BASE || "http://localhost:8000";

type Market = {
  market_id: string;
  question: string;
  category: string;
  volume_24h: number;
  liquidity: number;
  spread_bps: number;
  deterministic_priority?: number;
  ai_score?: number;
  ai_reasoning?: string;
  ai_tags?: string[];
};

export default function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [markets, setMarkets] = useState<Market[]>([]);
  const [useAi, setUseAi] = useState(true);
  const [optimizing, setOptimizing] = useState(false);

  const normalizedBase = useMemo(() => API_BASE.replace(/\/$/, ""), []);

  async function scoreMarket(market: Market): Promise<Market> {
    if (!useAi) {
      return { ...market, ai_score: undefined, ai_reasoning: undefined, ai_tags: [] };
    }
    try {
      const res = await fetch(`${normalizedBase}/api/v1/ai/score-market`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(market),
      });
      if (!res.ok) {
        return market;
      }
      const data = await res.json();
      return {
        ...market,
        ai_score: data?.score?.score,
        ai_reasoning: data?.score?.reasoning,
        ai_tags: data?.score?.tags || [],
      };
    } catch {
      return market;
    }
  }

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(
        `${normalizedBase}/api/v1/markets?min_volume_24h=1000&max_spread_bps=220`
      );
      if (!res.ok) {
        throw new Error(`API error: ${res.status}`);
      }
      const data = await res.json();
      const raw = (data.markets || []) as Market[];
      const withDeterministic = raw.map((m) => ({
        ...m,
        deterministic_priority:
          m.deterministic_priority ??
          Math.max(0, Math.min(10, (m.volume_24h / 150000) * 3 + (200 - m.spread_bps) / 30)),
      }));
      if (!useAi) {
        setMarkets(withDeterministic);
      } else {
        setOptimizing(true);
        const scored = await Promise.all(withDeterministic.map((m) => scoreMarket(m)));
        setMarkets(scored);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setError(message);
    } finally {
      setOptimizing(false);
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [useAi]);

  return (
    <SafeAreaView style={styles.root}>
      <ScrollView contentContainerStyle={styles.container}>
        <Text style={styles.title}>Polymarket AI Platform</Text>
        <Text style={styles.subtitle}>
          AI score is advisory only; deterministic rules remain authoritative.
        </Text>

        <View style={styles.controls}>
          <View style={styles.switchRow}>
            <Text style={styles.switchText}>AI assist</Text>
            <Switch value={useAi} onValueChange={setUseAi} />
          </View>
          <TouchableOpacity style={styles.button} onPress={load}>
            <Text style={styles.buttonText}>Refresh</Text>
          </TouchableOpacity>
        </View>

        {loading ? <ActivityIndicator size="large" color="#7c8cff" /> : null}
        {optimizing ? <Text style={styles.muted}>Scoring markets with AI...</Text> : null}
        {error ? <Text style={styles.error}>{error}</Text> : null}

        {markets.map((m) => (
          <View key={m.market_id} style={styles.card}>
            <Text style={styles.marketTitle}>{m.question}</Text>
            <Text style={styles.marketMeta}>
              Det: {(m.deterministic_priority ?? 0).toFixed(2)} | AI:{" "}
              {m.ai_score !== undefined ? m.ai_score.toFixed(2) : "n/a"}
            </Text>
            <Text style={styles.marketMeta}>
              {m.category.toUpperCase()} | Vol24h: ${m.volume_24h.toLocaleString()} | Liquidity: $
              {m.liquidity.toLocaleString()} | Spread: {m.spread_bps.toFixed(0)}bps
            </Text>
            {m.ai_reasoning ? <Text style={styles.reasoning}>{m.ai_reasoning}</Text> : null}
            {m.ai_tags?.length ? (
              <Text style={styles.tags}>Tags: {m.ai_tags.join(", ")}</Text>
            ) : null}
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: "#0d1020",
  },
  container: {
    padding: 16,
    gap: 12,
  },
  title: {
    fontSize: 26,
    color: "#f4f6ff",
    fontWeight: "700",
  },
  subtitle: {
    color: "#b9c0df",
    marginBottom: 12,
  },
  controls: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 8,
  },
  switchRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  switchText: {
    color: "#f4f6ff",
    fontWeight: "600",
  },
  button: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    backgroundColor: "#20253f",
    borderRadius: 10,
  },
  buttonText: {
    color: "#f4f6ff",
    fontWeight: "600",
  },
  error: {
    color: "#ff7b7b",
  },
  muted: {
    color: "#a8b0d1",
    fontSize: 12,
  },
  card: {
    backgroundColor: "#161a2e",
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#272d4f",
    padding: 12,
    gap: 6,
  },
  marketTitle: {
    color: "#f4f6ff",
    fontSize: 16,
    fontWeight: "600",
  },
  marketMeta: {
    color: "#bcc5ea",
    fontSize: 13,
  },
  reasoning: {
    color: "#9ca7d7",
    fontSize: 12,
    fontStyle: "italic",
  },
  tags: {
    color: "#8c95ba",
    fontSize: 11,
  },
});
