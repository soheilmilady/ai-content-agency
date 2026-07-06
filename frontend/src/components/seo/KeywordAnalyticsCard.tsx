"use client";

import type { KeywordEntry } from "@/hooks/useGoogleSuggest";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

// ─────────────────────────────────────────────
// SEO Analytics & Metric Calculations
// ─────────────────────────────────────────────

interface KeywordAnalyticsCardProps {
  results: KeywordEntry[];
  isRunning: boolean;
}

function classifyRichness(total: number): {
  label: string;
  emoji: string;
  color: string;
} {
  if (total > 200) return { label: "نیش طلایی — فوق‌العاده", emoji: "👑", color: "text-yellow-500" };
  if (total > 100) return { label: "نیش فوق عمیق", emoji: "🌟", color: "text-purple-400" };
  if (total > 40)  return { label: "جامع و عالی", emoji: "👍", color: "text-green-400" };
  return { label: "استاندارد / محدود", emoji: "📊", color: "text-muted-foreground" };
}

export default function KeywordAnalyticsCard({
  results,
  isRunning,
}: KeywordAnalyticsCardProps) {
  if (results.length === 0 && !isRunning) return null;

  const totalKeywords = results.length;

  // Long-Tail vs Short-Tail classification
  let longTailCount = 0;
  let shortTailCount = 0;
  let totalFrequency = 0;
  let maxFrequency = 0;

  for (const entry of results) {
    const wordCount = entry.keyword.split(/\s+/).length;
    if (wordCount >= 4) {
      longTailCount++;
    } else {
      shortTailCount++;
    }
    totalFrequency += entry.count;
    if (entry.count > maxFrequency) maxFrequency = entry.count;
  }

  const longTailRatio =
    totalKeywords > 0 ? Math.round((longTailCount / totalKeywords) * 100) : 0;

  const avgFrequency =
    totalKeywords > 0 ? (totalFrequency / totalKeywords).toFixed(1) : "0";

  const richness = classifyRichness(totalKeywords);

  // Unique layers discovered
  const layersUsed = new Set(results.map((r) => r.firstLayer)).size;

  return (
    <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          📈 تحلیل سئو لحظه‌ای
          {isRunning && (
            <span className="inline-block w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {/* Total Keywords */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className="text-2xl font-extrabold tabular-nums">{totalKeywords}</p>
            <p className="text-xs text-muted-foreground mt-1">کل کلمات کلیدی</p>
          </div>

          {/* Topic Richness */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className={`text-lg font-bold ${richness.color}`}>
              {richness.emoji} {richness.label}
            </p>
            <p className="text-xs text-muted-foreground mt-1">غنای موضوعی</p>
          </div>

          {/* Long-Tail Ratio */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className="text-2xl font-extrabold tabular-nums text-emerald-500">
              {longTailRatio}%
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              نسبت Long-Tail (ارزش بالا)
            </p>
          </div>

          {/* Long-Tail Count */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className="text-lg font-bold text-emerald-400">{longTailCount}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Long-Tail (≥۴ کلمه)
            </p>
          </div>

          {/* Short-Tail Count */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className="text-lg font-bold text-orange-400">{shortTailCount}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Short-Tail (&lt;۴ کلمه)
            </p>
          </div>

          {/* Avg Frequency */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className="text-lg font-bold tabular-nums">{avgFrequency}</p>
            <p className="text-xs text-muted-foreground mt-1">
              میانگین فرکانس
            </p>
          </div>

          {/* Max Frequency */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className="text-lg font-bold tabular-nums text-indigo-400">
              {maxFrequency}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              بیشترین تکرار
            </p>
          </div>

          {/* Layers Used */}
          <div className="rounded-xl bg-muted/30 p-3 text-center border border-border/30">
            <p className="text-lg font-bold tabular-nums">{layersUsed}</p>
            <p className="text-xs text-muted-foreground mt-1">
              لایه‌های کاوش‌شده
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
