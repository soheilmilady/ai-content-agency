"use client";

import { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Copy,
  ExternalLink,
  Sparkles,
  Square,
  Loader2,
  Languages,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import KeywordAnalyticsCard from "@/components/seo/KeywordAnalyticsCard";
import {
  useGoogleSuggest,
  type ScrapeConfig,
} from "@/hooks/useGoogleSuggest";

// ─────────────────────────────────────────────
// Language & Country Maps
// ─────────────────────────────────────────────
const LANGUAGES = [
  { value: "fa", label: "فارسی" },
  { value: "en", label: "English" },
  { value: "ar", label: "العربية" },
  { value: "tr", label: "Türkçe" },
  { value: "de", label: "Deutsch" },
  { value: "fr", label: "Français" },
  { value: "es", label: "Español" },
  { value: "ru", label: "Русский" },
  { value: "zh", label: "中文" },
  { value: "ja", label: "日本語" },
];

const COUNTRIES = [
  { value: "ir", label: "ایران 🇮🇷" },
  { value: "us", label: "آمریکا 🇺🇸" },
  { value: "gb", label: "انگلستان 🇬🇧" },
  { value: "ae", label: "امارات 🇦🇪" },
  { value: "tr", label: "ترکیه 🇹🇷" },
  { value: "de", label: "آلمان 🇩🇪" },
  { value: "fr", label: "فرانسه 🇫🇷" },
  { value: "sa", label: "عربستان 🇸🇦" },
];

// ─────────────────────────────────────────────
// Main Page Component
// ─────────────────────────────────────────────
export default function KeywordResearchPage() {
  const router = useRouter();
  const {
    results,
    isRunning,
    progress,
    startScraping,
    stopScraping,
    translations,
    isTranslating,
    translationProgress,
    translateResults,
    cancelTranslation,
  } = useGoogleSuggest();

  // ── Search Config State ──
  const [seed, setSeed] = useState("");
  const [language, setLanguage] = useState("fa");
  const [country, setCountry] = useState("ir");
  const [scanType, setScanType] = useState<"standard" | "deep">("standard");
  const [layers, setLayers] = useState(3);
  const [maxSeedsPerLayer, setMaxSeedsPerLayer] = useState(25);
  const [requestDelay, setRequestDelay] = useState(250);

  // ── UI State ──
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [filterText, setFilterText] = useState("");
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleStart = () => {
    if (!seed.trim()) return;
    const config: ScrapeConfig = {
      seed: seed.trim(),
      language,
      country,
      layers: scanType === "standard" ? 1 : layers,
      maxSeedsPerLayer,
      requestDelay,
    };
    startScraping(config);
  };

  const handleCopy = (keyword: string, index: number) => {
    navigator.clipboard.writeText(keyword);
    setCopiedIndex(index);
    if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    copyTimeoutRef.current = setTimeout(() => setCopiedIndex(null), 1500);
  };

  const handleOpenGoogle = (keyword: string) => {
    window.open(
      `https://www.google.com/search?q=${encodeURIComponent(keyword)}`,
      "_blank",
    );
  };

  // ── Magic Bridge: Navigate to Article Generator with keyword ──
  const handleGenerateArticle = (keyword: string) => {
    router.push(
      `/dashboard/articles/new?keyword=${encodeURIComponent(keyword)}`,
    );
  };

  // ── Filter results ──
  const filteredResults = filterText
    ? results.filter((r) => r.keyword.includes(filterText.toLowerCase()))
    : results;

  // ── Check if translation is applicable (non-Persian languages) ──
  const showTranslateButton = language !== "fa" && results.length > 0;

  return (
    <div dir="rtl" className="mx-auto max-w-6xl space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-extrabold tracking-tight flex items-center gap-2">
          <Search className="w-6 h-6 text-primary" />
          تحقیق کلمات کلیدی هوشمند
        </h2>
        <p className="text-muted-foreground mt-1">
          کشف خودکار کلمات کلیدی سئو از Google Autocomplete — با الگوریتم
          Alphabet Soup چندلایه
        </p>
      </div>

      {/* ═══════ Search Parameter Card ═══════ */}
      <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
        <CardHeader>
          <CardTitle className="text-base">پارامترهای جستجو</CardTitle>
          <CardDescription>
            کلمه کلیدی پایه را وارد کنید و تنظیمات اسکن را مشخص کنید
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          {/* Seed Keyword */}
          <div className="space-y-2">
            <Label>کلمه کلیدی پایه (Seed)</Label>
            <div className="flex gap-2">
              <Input
                placeholder="مثال: قهوه کلدبرو"
                value={seed}
                onChange={(e) => setSeed(e.target.value)}
                disabled={isRunning}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleStart();
                }}
                className="flex-1"
              />
              {!isRunning ? (
                <Button
                  onClick={handleStart}
                  disabled={!seed.trim()}
                  className="bg-primary hover:bg-primary/90 min-w-[120px]"
                >
                  <Search className="w-4 h-4 ml-2" />
                  شروع اسکن
                </Button>
              ) : (
                <Button
                  onClick={stopScraping}
                  variant="destructive"
                  className="min-w-[120px]"
                >
                  <Square className="w-4 h-4 ml-2" />
                  توقف
                </Button>
              )}
            </div>
          </div>

          {/* Scan Type */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label>نوع اسکن</Label>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setScanType("standard")}
                  disabled={isRunning}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold border transition-all ${
                    scanType === "standard"
                      ? "bg-primary text-primary-foreground border-primary shadow-md"
                      : "bg-muted/30 text-muted-foreground border-border/50 hover:bg-muted/50"
                  }`}
                >
                  استاندارد
                </button>
                <button
                  type="button"
                  onClick={() => setScanType("deep")}
                  disabled={isRunning}
                  className={`flex-1 py-2 px-3 rounded-lg text-sm font-semibold border transition-all ${
                    scanType === "deep"
                      ? "bg-primary text-primary-foreground border-primary shadow-md"
                      : "bg-muted/30 text-muted-foreground border-border/50 hover:bg-muted/50"
                  }`}
                >
                  عمیق (چندلایه)
                </button>
              </div>
            </div>

            {/* Layer Count (only for deep) */}
            {scanType === "deep" && (
              <div className="space-y-2">
                <Label>تعداد لایه‌ها: {layers}</Label>
                <input
                  type="range"
                  min={2}
                  max={10}
                  value={layers}
                  onChange={(e) => setLayers(Number(e.target.value))}
                  disabled={isRunning}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>۲</span>
                  <span>۱۰</span>
                </div>
              </div>
            )}

            {/* Language */}
            <div className="space-y-2">
              <Label>زبان هدف (hl)</Label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                disabled={isRunning}
                className="w-full border border-border/50 bg-background rounded-lg p-2 text-sm"
              >
                {LANGUAGES.map((l) => (
                  <option key={l.value} value={l.value}>
                    {l.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Country */}
            <div className="space-y-2">
              <Label>کشور هدف (gl)</Label>
              <select
                value={country}
                onChange={(e) => setCountry(e.target.value)}
                disabled={isRunning}
                className="w-full border border-border/50 bg-background rounded-lg p-2 text-sm"
              >
                {COUNTRIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Advanced settings (collapsible) */}
          {scanType === "deep" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-border/30">
              <div className="space-y-2">
                <Label>حداکثر Seed هر لایه: {maxSeedsPerLayer}</Label>
                <input
                  type="range"
                  min={5}
                  max={100}
                  step={5}
                  value={maxSeedsPerLayer}
                  onChange={(e) => setMaxSeedsPerLayer(Number(e.target.value))}
                  disabled={isRunning}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>۵</span>
                  <span>۱۰۰</span>
                </div>
              </div>
              <div className="space-y-2">
                <Label>تأخیر بین درخواست‌ها: {requestDelay}ms</Label>
                <input
                  type="range"
                  min={50}
                  max={2000}
                  step={50}
                  value={requestDelay}
                  onChange={(e) => setRequestDelay(Number(e.target.value))}
                  disabled={isRunning}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>50ms</span>
                  <span>2000ms</span>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* ═══════ Live Progress Monitor ═══════ */}
      {isRunning && (
        <Card className="border-primary/30 bg-card/80 backdrop-blur-sm animate-in fade-in duration-300">
          <CardContent className="pt-6 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                <span className="text-sm font-bold">{progress.phase}</span>
              </div>
              <Badge variant="secondary" className="tabular-nums">
                لایه {progress.currentLayer} از {progress.totalLayers}
              </Badge>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-muted/40 rounded-full h-2.5 overflow-hidden">
              <div
                className="h-full bg-gradient-to-l from-primary to-primary/70 rounded-full transition-all duration-300 ease-out"
                style={{ width: `${progress.percentage}%` }}
              />
            </div>

            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span className="truncate max-w-[50%]" dir="ltr">
                {progress.currentQuery}
              </span>
              <div className="flex gap-4">
                <span className="tabular-nums">
                  {progress.processed}/{progress.total}
                </span>
                <span className="font-bold text-foreground tabular-nums">
                  🔑 {progress.uniqueKeywords} کلمه
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ═══════ Analytics Card ═══════ */}
      <KeywordAnalyticsCard results={results} isRunning={isRunning} />

      {/* ═══════ Results Table ═══════ */}
      {results.length > 0 && (
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          <CardHeader className="pb-3">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <CardTitle className="text-base">
                نتایج کشف‌شده ({filteredResults.length.toLocaleString("fa-IR")}{" "}
                کلمه)
              </CardTitle>
              <div className="flex gap-2 flex-wrap">
                {/* Translation Button */}
                {showTranslateButton && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      isTranslating
                        ? cancelTranslation()
                        : translateResults(language)
                    }
                    disabled={isRunning}
                    className="text-xs"
                  >
                    {isTranslating ? (
                      <>
                        <XCircle className="w-3.5 h-3.5 ml-1.5" />
                        لغو ترجمه ({translationProgress.processed}/
                        {translationProgress.total})
                      </>
                    ) : (
                      <>
                        <Languages className="w-3.5 h-3.5 ml-1.5" />
                        ترجمه فارسی
                      </>
                    )}
                  </Button>
                )}

                {/* Filter input */}
                <Input
                  placeholder="فیلتر نتایج..."
                  value={filterText}
                  onChange={(e) => setFilterText(e.target.value)}
                  className="w-40 h-8 text-xs"
                />
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="max-h-[600px] overflow-y-auto rounded-lg border border-border/30">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-muted/80 backdrop-blur-sm z-10">
                  <tr className="text-xs text-muted-foreground">
                    <th className="text-right py-2.5 px-3 font-semibold">#</th>
                    <th className="text-right py-2.5 px-3 font-semibold">
                      کلمه کلیدی
                    </th>
                    {Object.keys(translations).length > 0 && (
                      <th className="text-right py-2.5 px-3 font-semibold">
                        ترجمه فارسی
                      </th>
                    )}
                    <th className="text-center py-2.5 px-3 font-semibold">
                      فرکانس
                    </th>
                    <th className="text-center py-2.5 px-3 font-semibold">
                      لایه
                    </th>
                    <th className="text-center py-2.5 px-3 font-semibold">
                      نوع
                    </th>
                    <th className="text-center py-2.5 px-3 font-semibold">
                      اقدام
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/20">
                  {filteredResults.map((entry, index) => {
                    const wordCount = entry.keyword.split(/\s+/).length;
                    const isLongTail = wordCount >= 4;
                    return (
                      <tr
                        key={entry.keyword}
                        className="hover:bg-muted/20 transition-colors"
                      >
                        <td className="py-2 px-3 text-muted-foreground text-xs tabular-nums">
                          {index + 1}
                        </td>
                        <td className="py-2 px-3 font-medium" dir="auto">
                          {entry.keyword}
                        </td>
                        {Object.keys(translations).length > 0 && (
                          <td
                            className="py-2 px-3 text-muted-foreground text-xs"
                            dir="rtl"
                          >
                            {translations[entry.keyword] || "—"}
                          </td>
                        )}
                        <td className="py-2 px-3 text-center">
                          <Badge
                            variant="secondary"
                            className="tabular-nums text-xs"
                          >
                            {entry.count}
                          </Badge>
                        </td>
                        <td className="py-2 px-3 text-center text-xs text-muted-foreground tabular-nums">
                          L{entry.firstLayer}
                        </td>
                        <td className="py-2 px-3 text-center">
                          <Badge
                            variant={isLongTail ? "default" : "outline"}
                            className={`text-[10px] ${
                              isLongTail
                                ? "bg-emerald-500/15 text-emerald-500 border-emerald-500/30"
                                : ""
                            }`}
                          >
                            {isLongTail ? "Long-Tail" : "Short"}
                          </Badge>
                        </td>
                        <td className="py-2 px-3 text-center">
                          <div className="flex items-center justify-center gap-1">
                            {/* Copy */}
                            <button
                              type="button"
                              title="کپی"
                              onClick={() =>
                                handleCopy(entry.keyword, index)
                              }
                              className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
                            >
                              {copiedIndex === index ? (
                                <span className="text-[10px] text-green-500 font-bold">
                                  ✓
                                </span>
                              ) : (
                                <Copy className="w-3.5 h-3.5" />
                              )}
                            </button>

                            {/* Open in Google */}
                            <button
                              type="button"
                              title="جستجو در گوگل"
                              onClick={() => handleOpenGoogle(entry.keyword)}
                              className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </button>

                            {/* ✨ Magic Bridge: Generate AI Article */}
                            <button
                              type="button"
                              title="✨ تولید مقاله AI"
                              onClick={() =>
                                handleGenerateArticle(entry.keyword)
                              }
                              className="p-1.5 rounded-md hover:bg-primary/10 transition-colors text-primary hover:text-primary"
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
