"use client";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface AIScoreBadgeProps {
  score?: number | null;
  reasoning?: string | null;
  tags?: string[];
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

function getScoreColor(score: number): string {
  if (score >= 7.5) return "bg-emerald-500/20 text-emerald-300 border-emerald-500/30";
  if (score >= 6.0) return "bg-blue-500/20 text-blue-300 border-blue-500/30";
  if (score >= 4.5) return "bg-yellow-500/20 text-yellow-300 border-yellow-500/30";
  return "bg-red-500/20 text-red-300 border-red-500/30";
}

function getScoreLabel(score: number): string {
  if (score >= 8.0) return "High conviction";
  if (score >= 6.5) return "Moderate signal";
  if (score >= 5.0) return "Weak signal";
  return "Low quality";
}

export function AIScoreBadge({
  score,
  reasoning,
  tags = [],
  size = "md",
  showLabel = false,
}: AIScoreBadgeProps) {
  if (score === null || score === undefined) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-gray-700/50 text-gray-400 border border-gray-600/30">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
        Not scored
      </span>
    );
  }

  const colorClass = getScoreColor(score);
  const label = getScoreLabel(score);

  const badge = (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border cursor-help font-medium",
        colorClass,
        size === "sm" && "px-1.5 py-0.5 text-xs",
        size === "md" && "px-2 py-0.5 text-xs",
        size === "lg" && "px-3 py-1 text-sm",
      )}
    >
      <span className="opacity-70">🤖</span>
      <span>{score.toFixed(1)}</span>
      {showLabel && <span className="opacity-80">{label}</span>}
    </span>
  );

  if (!reasoning && tags.length === 0) return badge;

  return (
    <TooltipProvider>
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent className="max-w-xs bg-gray-900 border-gray-700 p-3">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-white font-semibold">AI Score: {score.toFixed(1)}/10</span>
              <span className="text-xs text-gray-400">({label})</span>
            </div>
            {reasoning && (
              <p className="text-gray-300 text-xs leading-relaxed">{reasoning}</p>
            )}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tags.map((tag) => (
                  <span
                    key={tag}
                    className="px-1.5 py-0.5 bg-gray-700 rounded text-xs text-gray-300"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
            <p className="text-gray-500 text-xs italic">
              AI is advisory only. Risk engine has final authority.
            </p>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
