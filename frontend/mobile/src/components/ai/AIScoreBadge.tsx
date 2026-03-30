import React from "react";
import { View, Text, StyleSheet } from "react-native";

interface Props {
  score?: number | null;
  size?: "sm" | "md" | "lg";
}

function getColor(score: number) {
  if (score >= 7.5) return { bg: "rgba(16,185,129,0.2)", text: "#6EE7B7", border: "rgba(16,185,129,0.3)" };
  if (score >= 6.0) return { bg: "rgba(59,130,246,0.2)", text: "#93C5FD", border: "rgba(59,130,246,0.3)" };
  if (score >= 4.5) return { bg: "rgba(245,158,11,0.2)", text: "#FCD34D", border: "rgba(245,158,11,0.3)" };
  return { bg: "rgba(239,68,68,0.2)", text: "#FCA5A5", border: "rgba(239,68,68,0.3)" };
}

export function AIScoreBadge({ score, size = "md" }: Props) {
  if (score == null) {
    return (
      <View style={styles.notScored}>
        <Text style={styles.notScoredText}>–</Text>
      </View>
    );
  }

  const colors = getColor(score);
  const fontSize = size === "sm" ? 10 : size === "lg" ? 14 : 12;

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: colors.bg,
          borderColor: colors.border,
        },
      ]}
    >
      <Text style={[styles.icon, { fontSize }]}>🤖</Text>
      <Text style={[styles.score, { color: colors.text, fontSize }]}>
        {score.toFixed(1)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    borderWidth: 1,
  },
  icon: {
    lineHeight: 16,
  },
  score: {
    fontWeight: "700",
  },
  notScored: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 20,
    backgroundColor: "rgba(63,63,70,0.5)",
  },
  notScoredText: {
    color: "#71717A",
    fontSize: 11,
  },
});
