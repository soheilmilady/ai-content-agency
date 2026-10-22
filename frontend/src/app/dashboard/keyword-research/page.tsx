"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  Loader2,
  Languages,
  XCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import KeywordAnalyticsCard from "@/components/seo/KeywordAnalyticsCard";
import { KeywordSearchForm } from "@/components/seo/KeywordSearchForm";
import { KeywordResultsTable } from "@/components/seo/KeywordResultsTable";
import { TopicClusterCard, type ClusterData } from "@/components/seo/TopicClusterCard";
import { useGoogleSuggest, type ScrapeConfig } from "@/hooks/useGoogleSuggest";
import { clusterKeywords } from "@/lib/api";

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
  const [currentPage, setCurrentPage] = useState(1);
  const PAGE_SIZE = 50;
  const [viewMode, setViewMode] = useState<"list" | "clusters">("list");
  const [clusters, setClusters] = useState<ClusterData[]>([]);
  const [isClustering, setIsClustering] = useState(false);
  const [clusterError, setClusterError] = useState("");
  const copyTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Restore clusters from sessionStorage on mount
  useEffect(() => {
    try {
      const savedClusters = sessionStorage.getItem("keyword_clusters_cache");
      if (savedClusters) {
        setClusters(JSON.parse(savedClusters));
      }
    } catch {
      // ignore storage error
    }
  }, []);

  const handleStart = () => {
    if (!seed.trim()) return;
    setCurrentPage(1);
    setClusterError("");
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

  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current);
    };
  }, []);

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

  const handleCluster = async () => {
    if (results.length === 0) return;
    setIsClustering(true);
    setViewMode("clusters");
    setClusterError("");

    const topKeywords = results.slice(0, 50).map((r) => r.keyword);

    try {
      const data = await clusterKeywords(topKeywords);
      const newClusters = data.clusters || [];
      setClusters(newClusters);
      try {
        sessionStorage.setItem("keyword_clusters_cache", JSON.stringify(newClusters));
      } catch {
        // ignore storage error
      }
    } catch (err) {
      console.error(err);
      const axiosError = err as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosError.response?.status !== 401) {
        setClusterError(axiosError.response?.data?.detail || "خطا در ارتباط با هوش مصنوعی برای خوشه‌بندی معنایی.");
        setViewMode("list");
      }
    } finally {
      setIsClustering(false);
    }
  };

  // ── Filter & Pagination ──
  const filteredResults = filterText
    ? results.filter((r) => r.keyword.includes(filterText.toLowerCase()))
    : results;

  const totalPages = Math.max(1, Math.ceil(filteredResults.length / PAGE_SIZE));
  const activePage = Math.min(currentPage, totalPages);
  const paginatedResults = filteredResults.slice(
    (activePage - 1) * PAGE_SIZE,
    activePage * PAGE_SIZE,
  );

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
      <KeywordSearchForm
        seed={seed}
        setSeed={setSeed}
        scanType={scanType}
        setScanType={setScanType}
        layers={layers}
        setLayers={setLayers}
        language={language}
        setLanguage={setLanguage}
        country={country}
        setCountry={setCountry}
        maxSeedsPerLayer={maxSeedsPerLayer}
        setMaxSeedsPerLayer={setMaxSeedsPerLayer}
        requestDelay={requestDelay}
        setRequestDelay={setRequestDelay}
        isRunning={isRunning}
        onStart={handleStart}
        onStop={stopScraping}
        languages={LANGUAGES}
        countries={COUNTRIES}
      />

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

      {/* ═══════ Results Section ═══════ */}
      {results.length > 0 && (
        <Card className="border-border/50 bg-card/80 backdrop-blur-sm">
          {clusterError && (
            <div className="mx-6 mt-4 p-3 bg-destructive/10 border border-destructive/20 text-destructive rounded-lg text-sm flex justify-between items-center">
              <span>{clusterError}</span>
              <button
                onClick={() => setClusterError("")}
                className="text-xs hover:underline text-muted-foreground mr-2"
              >
                بستن
              </button>
            </div>
          )}
          <CardHeader className="pb-3 border-b border-border/30 mb-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
              <div className="flex items-center gap-4">
                <CardTitle className="text-base">
                  نتایج کشف‌شده ({filteredResults.length.toLocaleString("fa-IR")} کلمه)
                </CardTitle>
                <div className="flex bg-muted/50 p-1 rounded-md">
                  <button
                    onClick={() => setViewMode("list")}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-sm transition-all ${
                      viewMode === "list"
                        ? "bg-background shadow-sm text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    📋 لیست ساده
                  </button>
                  <button
                    onClick={() => {
                      if (clusters.length > 0) setViewMode("clusters");
                      else handleCluster();
                    }}
                    className={`px-3 py-1.5 text-xs font-semibold rounded-sm transition-all ${
                      viewMode === "clusters"
                        ? "bg-background shadow-sm text-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    🗂️ خوشه‌های موضوعی
                  </button>
                </div>
              </div>

              <div className="flex gap-2 flex-wrap">
                {/* Cluster Button */}
                <Button
                  onClick={handleCluster}
                  disabled={isRunning || isClustering}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm text-xs h-8"
                >
                  {isClustering ? (
                    <Loader2 className="w-3.5 h-3.5 ml-1.5 animate-spin" />
                  ) : (
                    <span className="text-base mr-1 ml-1">🧠</span>
                  )}
                  {isClustering ? "در حال پردازش..." : "خوشه‌بندی با AI"}
                </Button>

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
            {viewMode === "clusters" ? (
              <div className="space-y-6">
                {isClustering ? (
                  <div className="py-12 flex flex-col items-center justify-center text-muted-foreground animate-pulse">
                    <span className="text-4xl mb-4">🧠</span>
                    <p className="text-sm font-semibold">
                      هوش مصنوعی در حال تحلیل معنایی و ساخت خوشه‌ها...
                    </p>
                    <p className="text-xs mt-2">این عملیات ممکن است چند ثانیه زمان ببرد.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {clusters.map((cluster, idx) => (
                      <TopicClusterCard key={idx} cluster={cluster} />
                    ))}
                    {clusters.length === 0 && !isClustering && (
                      <div className="col-span-full py-8 text-center text-muted-foreground">
                        خوشه‌ای یافت نشد. لطفاً دوباره تلاش کنید.
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <KeywordResultsTable
                paginatedResults={paginatedResults}
                translations={translations}
                activePage={activePage}
                pageSize={PAGE_SIZE}
                totalPages={totalPages}
                totalFilteredCount={filteredResults.length}
                onPageChange={setCurrentPage}
                onCopy={handleCopy}
                copiedIndex={copiedIndex}
                onOpenGoogle={handleOpenGoogle}
                onGenerateArticle={handleGenerateArticle}
              />
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
