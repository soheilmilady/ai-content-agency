"use client";

import { useState, useRef, useCallback } from "react";

// ─────────────────────────────────────────────
// Native Alphabet Character Sets (per language)
// ─────────────────────────────────────────────
const ALPHABETS: Record<string, string[]> = {
  fa: [
    "ا", "ب", "پ", "ت", "ث", "ج", "چ", "ح", "خ", "د",
    "ذ", "ر", "ز", "ژ", "س", "ش", "ص", "ض", "ط", "ظ",
    "ع", "غ", "ف", "ق", "ک", "گ", "ل", "م", "ن", "و",
    "ه", "ی",
  ],
  en: "abcdefghijklmnopqrstuvwxyz".split(""),
  ar: [
    "ا", "ب", "ت", "ث", "ج", "ح", "خ", "د", "ذ", "ر",
    "ز", "س", "ش", "ص", "ض", "ط", "ظ", "ع", "غ", "ف",
    "ق", "ك", "ل", "م", "ن", "ه", "و", "ي",
  ],
  de: "abcdefghijklmnopqrstuvwxyzäöüß".split(""),
  fr: "abcdefghijklmnopqrstuvwxyzéèêëàâçîïôùûü".split(""),
  es: "abcdefghijklmnopqrstuvwxyzñ".split(""),
  ru: [
    "а", "б", "в", "г", "д", "е", "ё", "ж", "з", "и",
    "й", "к", "л", "м", "н", "о", "п", "р", "с", "т",
    "у", "ф", "х", "ц", "ч", "ш", "щ", "э", "ю", "я",
  ],
  tr: "abcçdefgğhıijklmnoöprsştuüvyz".split(""),
  zh: "abcdefghijklmnopqrstuvwxyz".split(""), // pinyin fallback
  ja: "abcdefghijklmnopqrstuvwxyz".split(""), // romaji fallback
};

// ─────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────
export interface KeywordEntry {
  keyword: string;
  count: number;
  firstLayer: number;
}

export interface ScrapeConfig {
  seed: string;
  language: string;   // hl param (e.g. "fa", "en")
  country: string;    // gl param (e.g. "ir", "us")
  layers: number;     // 1 = standard, 2-10 = deep multi-layer
  maxSeedsPerLayer: number; // default 25
  requestDelay: number;     // ms, default 250
}

export interface ScrapeProgress {
  phase: string;
  currentQuery: string;
  processed: number;
  total: number;
  percentage: number;
  uniqueKeywords: number;
  currentLayer: number;
  totalLayers: number;
}

export interface TranslationProgress {
  processed: number;
  total: number;
}

// ─────────────────────────────────────────────
// Utility: Async sleep
// ─────────────────────────────────────────────
const sleep = (ms: number): Promise<void> =>
  new Promise((resolve) => setTimeout(resolve, ms));

// ─────────────────────────────────────────────
// Refinement 2: Persian & SEO String Normalization
// Converts ZWNJ (half-space) to space, collapses
// multiple whitespace, trims, and lowercases.
// ─────────────────────────────────────────────
const normalizeKeyword = (str: string): string => {
  if (!str) return "";
  return str
    .replace(/\u200C/g, " ")   // Persian Zero-Width Non-Joiner → space
    .replace(/\s+/g, " ")      // Collapse multiple spaces
    .trim()
    .toLowerCase();
};

// ─────────────────────────────────────────────
// Circuit Breaker: Max Consecutive Errors
// ─────────────────────────────────────────────
const MAX_CONSECUTIVE_ERRORS = 3;

// ─────────────────────────────────────────────
// JSONP Fetch — Google Autocomplete via Script Injection
// Refinement 1: Zombie Request Race Condition (No-op Fallback)
// ─────────────────────────────────────────────

/** Sentinel value returned when a network error occurs (vs empty results) */
const NETWORK_ERROR_SENTINEL: string[] | null = null;

function fetchJSONP(
  query: string,
  lang: string,
  country: string,
): Promise<string[] | null> {
  return new Promise((resolve) => {
    const callbackName = `googleSuggestCallback_${Math.floor(Math.random() * 2147483647)}`;
    const script = document.createElement("script");
    script.id = callbackName; // Tag for cleanup identification
    let settled = false;

    const win = window as unknown as Record<string, unknown>;

    // ── Zombie-safe cleanup: replace callback with No-op ──
    function handleSettled() {
      // Remove the script tag from DOM immediately
      const el = document.getElementById(callbackName);
      if (el) el.remove();

      // Replace callback with No-op to absorb late responses safely
      if (typeof window !== "undefined" && win[callbackName]) {
        win[callbackName] = () => {
          /* No-op: Late response safely ignored */
        };
        // Final garbage collection after 30 seconds
        setTimeout(() => {
          try {
            delete win[callbackName];
          } catch {
            win[callbackName] = undefined;
          }
        }, 30000);
      }
    }

    // ── Primary timeout: 4000ms ──
    const timeout = setTimeout(() => {
      if (!settled) {
        settled = true;
        handleSettled();
        resolve([]); // Timeout = empty results (not a network error)
      }
    }, 4000);

    // ── Success callback ──
    win[callbackName] = (data: unknown) => {
      if (settled) return;
      settled = true;
      clearTimeout(timeout);
      handleSettled();
      try {
        const arr = data as unknown[];
        const suggestions = Array.isArray(arr[1]) ? arr[1] : [];
        resolve(
          suggestions.filter(
            (s): s is string => typeof s === "string" && s.trim().length > 0,
          ),
        );
      } catch {
        resolve([]);
      }
    };

    // ── Build script URL ──
    script.src =
      `https://suggestqueries.google.com/complete/search` +
      `?client=chrome` +
      `&q=${encodeURIComponent(query)}` +
      `&hl=${encodeURIComponent(lang)}` +
      `&gl=${encodeURIComponent(country)}` +
      `&callback=${callbackName}`;

    // ── Network error handler ──
    script.onerror = () => {
      if (!settled) {
        settled = true;
        clearTimeout(timeout);
        handleSettled();
        resolve(NETWORK_ERROR_SENTINEL); // null = network failure
      }
    };

    document.head.appendChild(script);
  });
}

// ─────────────────────────────────────────────
// GTX Translation Engine (Google Translate — client-side)
// ─────────────────────────────────────────────
async function translateToFa(
  text: string,
  sourceLang: string,
  signal?: AbortSignal,
): Promise<string> {
  try {
    const res = await fetch(
      `https://translate.googleapis.com/translate_a/single` +
        `?client=gtx&sl=${encodeURIComponent(sourceLang)}&tl=fa&dt=t` +
        `&q=${encodeURIComponent(text)}`,
      { signal },
    );
    if (!res.ok) return text;
    const data = await res.json();
    // GTX response shape: [[["translation","original",...],...],...]
    if (Array.isArray(data) && Array.isArray(data[0]) && Array.isArray(data[0][0])) {
      return data[0][0][0] || text;
    }
    return text;
  } catch {
    return text; // graceful fallback on abort/network error
  }
}

// ─────────────────────────────────────────────
// 3-Tier Priority Sorting
// ─────────────────────────────────────────────
function sortKeywords(
  map: Map<string, { count: number; firstLayer: number }>,
  lang: string,
): KeywordEntry[] {
  const entries: KeywordEntry[] = Array.from(map.entries()).map(
    ([keyword, data]) => ({
      keyword,
      count: data.count,
      firstLayer: data.firstLayer,
    }),
  );

  return entries.sort((a, b) => {
    // 1. Frequency Score — Descending
    if (b.count !== a.count) return b.count - a.count;
    // 2. Discovery Layer — Ascending (closer to root = higher priority)
    if (a.firstLayer !== b.firstLayer) return a.firstLayer - b.firstLayer;
    // 3. Alphabetical Fallback — locale-aware
    return a.keyword.localeCompare(b.keyword, lang);
  });
}

// ─────────────────────────────────────────────
// Main Hook: useGoogleSuggest
// ─────────────────────────────────────────────
export function useGoogleSuggest() {
  // --- Scraping State ---
  const [results, setResults] = useState<KeywordEntry[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState<ScrapeProgress>({
    phase: "",
    currentQuery: "",
    processed: 0,
    total: 0,
    percentage: 0,
    uniqueKeywords: 0,
    currentLayer: 0,
    totalLayers: 0,
  });

  // --- Translation State ---
  const [translations, setTranslations] = useState<Record<string, string>>({});
  const [isTranslating, setIsTranslating] = useState(false);
  const [translationProgress, setTranslationProgress] =
    useState<TranslationProgress>({ processed: 0, total: 0 });

  // --- Internal Refs (no re-renders) ---
  const keywordMapRef = useRef(
    new Map<string, { count: number; firstLayer: number }>(),
  );
  const visitedQueriesRef = useRef(new Set<string>());
  const abortRef = useRef(false);
  const translationAbortRef = useRef<AbortController | null>(null);

  // ── Register a discovered keyword into the Map ──
  const registerKeyword = (keyword: string, layer: number): void => {
    const normalized = normalizeKeyword(keyword);
    if (!normalized) return;

    const map = keywordMapRef.current;
    const existing = map.get(normalized);
    if (existing) {
      existing.count += 1;
    } else {
      map.set(normalized, { count: 1, firstLayer: layer });
    }
  };

  // ── Process a single JSONP query and register results ──
  // Returns: string[] on success, null on network error (for circuit breaker)
  const processQuery = useCallback(async (
    query: string,
    layer: number,
    lang: string,
    country: string,
    delay: number,
  ): Promise<string[] | null> => {
    // Deduplication: never send the same query twice
    const normalizedQuery = normalizeKeyword(query);
    if (visitedQueriesRef.current.has(normalizedQuery)) {
      return [];
    }
    visitedQueriesRef.current.add(normalizedQuery);

    const suggestions = await fetchJSONP(query, lang, country);

    // Network error sentinel: propagate null upward for circuit breaker
    if (suggestions === null) {
      return null;
    }

    const newKeywords: string[] = [];
    for (const kw of suggestions) {
      const normalized = normalizeKeyword(kw);
      if (!normalized) continue;

      const isNew = !keywordMapRef.current.has(normalized);
      registerKeyword(normalized, layer);
      if (isNew) newKeywords.push(normalized);
    }

    // Throttle between consecutive requests
    if (delay > 0) await sleep(delay);

    return newKeywords;
  }, []);

  // ═══════════════════════════════════════════
  // START SCRAPING — Main Entry Point
  // ═══════════════════════════════════════════
  const startScraping = useCallback(async (config: ScrapeConfig) => {
    const {
      seed,
      language,
      country,
      layers,
      maxSeedsPerLayer,
      requestDelay,
    } = config;

    // Reset all state
    keywordMapRef.current = new Map();
    visitedQueriesRef.current = new Set();
    abortRef.current = false;
    setResults([]);
    setTranslations({});
    setIsRunning(true);

    const alphabet = ALPHABETS[language] || ALPHABETS.en;
    const seedTrimmed = seed.trim();

    // ───────────────────────────────────────
    // LAYER 1: Alphabet Soup
    // ───────────────────────────────────────
    // Queue: exact seed + suffix combos + prefix combos
    const layer1Queue: string[] = [seedTrimmed];
    for (const letter of alphabet) {
      layer1Queue.push(`${seedTrimmed} ${letter}`); // suffix
      layer1Queue.push(`${letter} ${seedTrimmed}`); // prefix
    }

    const totalLayer1 = layer1Queue.length;
    let processedLayer1 = 0;

    setProgress({
      phase: "لایه ۱ — سوپ الفبایی",
      currentQuery: "",
      processed: 0,
      total: totalLayer1,
      percentage: 0,
      uniqueKeywords: 0,
      currentLayer: 1,
      totalLayers: layers,
    });

    // Track keywords first discovered in layer 1 (for seeding layer 2)
    const layer1Discoveries: string[] = [];
    let consecutiveErrors = 0;

    for (const query of layer1Queue) {
      if (abortRef.current) break;

      // Circuit Breaker: stop after MAX_CONSECUTIVE_ERRORS network failures
      if (consecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
        setProgress((prev) => ({
          ...prev,
          phase: "⚠️ اتصال اینترنت ناپایدار — نتایج جمع‌آوری‌شده نمایش داده می‌شود",
        }));
        break;
      }

      setProgress((prev) => ({ ...prev, currentQuery: query }));

      const newKws = await processQuery(
        query,
        1,
        language,
        country,
        requestDelay,
      );

      if (newKws === null) {
        consecutiveErrors++;
        processedLayer1++;
        continue;
      }
      consecutiveErrors = 0; // Reset on success
      layer1Discoveries.push(...newKws);

      processedLayer1++;
      setProgress((prev) => ({
        ...prev,
        processed: processedLayer1,
        total: totalLayer1,
        percentage: Math.round((processedLayer1 / totalLayer1) * 100),
        uniqueKeywords: keywordMapRef.current.size,
      }));
    }

    // Publish sorted results after Layer 1
    setResults(sortKeywords(keywordMapRef.current, language));

    // ───────────────────────────────────────
    // LAYERS 2 to N: Recursive Direct Seed Queries
    // ───────────────────────────────────────
    let previousLayerDiscoveries = layer1Discoveries;

    for (let layer = 2; layer <= layers; layer++) {
      if (abortRef.current) break;

      // Select top seeds from PREVIOUS layer's newly-discovered keywords
      // Sort candidates by their frequency score (descending), cap to maxSeedsPerLayer
      const candidates = previousLayerDiscoveries
        .map((kw) => {
          const data = keywordMapRef.current.get(kw);
          return data ? { keyword: kw, count: data.count } : null;
        })
        .filter(
          (c): c is { keyword: string; count: number } =>
            c !== null && !visitedQueriesRef.current.has(c.keyword),
        )
        .sort((a, b) => b.count - a.count)
        .slice(0, maxSeedsPerLayer);

      if (candidates.length === 0) {
        // No new seeds to explore — finish early
        break;
      }

      const totalLayerN = candidates.length;
      let processedLayerN = 0;

      setProgress({
        phase: `لایه ${layer} — استخراج عمیق`,
        currentQuery: "",
        processed: 0,
        total: totalLayerN,
        percentage: 0,
        uniqueKeywords: keywordMapRef.current.size,
        currentLayer: layer,
        totalLayers: layers,
      });

      const currentLayerDiscoveries: string[] = [];
      let layerConsecutiveErrors = 0;

      for (const { keyword: seedQuery } of candidates) {
        if (abortRef.current) break;

        // Circuit Breaker per layer
        if (layerConsecutiveErrors >= MAX_CONSECUTIVE_ERRORS) {
          setProgress((prev) => ({
            ...prev,
            phase: `⚠️ لایه ${layer} — اتصال ناپایدار، نتایج موجود ذخیره شد`,
          }));
          break;
        }

        setProgress((prev) => ({ ...prev, currentQuery: seedQuery }));

        const newKws = await processQuery(
          seedQuery,
          layer,
          language,
          country,
          requestDelay,
        );

        if (newKws === null) {
          layerConsecutiveErrors++;
          processedLayerN++;
          continue;
        }
        layerConsecutiveErrors = 0;
        currentLayerDiscoveries.push(...newKws);

        processedLayerN++;
        setProgress((prev) => ({
          ...prev,
          processed: processedLayerN,
          total: totalLayerN,
          percentage: Math.round((processedLayerN / totalLayerN) * 100),
          uniqueKeywords: keywordMapRef.current.size,
        }));
      }

      // Publish updated results after each layer
      setResults(sortKeywords(keywordMapRef.current, language));

      // Pass this layer's discoveries as seeds for the next layer
      previousLayerDiscoveries = currentLayerDiscoveries;
    }

    // ── Final publish ──
    setResults(sortKeywords(keywordMapRef.current, language));
    setProgress((prev) => ({
      ...prev,
      phase: "تکمیل شد ✅",
      percentage: 100,
    }));
    setIsRunning(false);
  }, [processQuery]);

  // ═══════════════════════════════════════════
  // STOP SCRAPING — Abort all operations
  // ═══════════════════════════════════════════
  const stopScraping = useCallback(() => {
    abortRef.current = true;
    // Also abort any running translation
    if (translationAbortRef.current) {
      translationAbortRef.current.abort();
      translationAbortRef.current = null;
    }
  }, []);

  // ═══════════════════════════════════════════
  // BULK TRANSLATE — Sequential GTX Translation
  // ═══════════════════════════════════════════
  const translateResults = useCallback(
    async (sourceLang: string) => {
      // Cancel any previous translation batch
      if (translationAbortRef.current) {
        translationAbortRef.current.abort();
      }

      const controller = new AbortController();
      translationAbortRef.current = controller;

      setIsTranslating(true);
      setTranslationProgress({ processed: 0, total: results.length });
      const newTranslations: Record<string, string> = {};

      for (let i = 0; i < results.length; i++) {
        if (controller.signal.aborted) break;

        const entry = results[i];
        const translation = await translateToFa(
          entry.keyword,
          sourceLang,
          controller.signal,
        );
        newTranslations[entry.keyword] = translation;

        setTranslationProgress({ processed: i + 1, total: results.length });
        setTranslations({ ...newTranslations });

        // 100ms delay between translation requests to avoid IP blocking
        if (i < results.length - 1) {
          await sleep(100);
        }
      }

      setIsTranslating(false);
      translationAbortRef.current = null;
    },
    [results],
  );

  // ── Cancel translation only ──
  const cancelTranslation = useCallback(() => {
    if (translationAbortRef.current) {
      translationAbortRef.current.abort();
      translationAbortRef.current = null;
    }
    setIsTranslating(false);
  }, []);

  return {
    // Scraping
    results,
    isRunning,
    progress,
    startScraping,
    stopScraping,

    // Translation
    translations,
    isTranslating,
    translationProgress,
    translateResults,
    cancelTranslation,
  };
}
