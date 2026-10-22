"use client";

import { Search, Square } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export interface KeywordSearchFormProps {
  seed: string;
  setSeed: (s: string) => void;
  scanType: "standard" | "deep";
  setScanType: (t: "standard" | "deep") => void;
  layers: number;
  setLayers: (l: number) => void;
  language: string;
  setLanguage: (lang: string) => void;
  country: string;
  setCountry: (c: string) => void;
  maxSeedsPerLayer: number;
  setMaxSeedsPerLayer: (n: number) => void;
  requestDelay: number;
  setRequestDelay: (n: number) => void;
  isRunning: boolean;
  onStart: () => void;
  onStop: () => void;
  languages: { value: string; label: string }[];
  countries: { value: string; label: string }[];
}

export function KeywordSearchForm({
  seed,
  setSeed,
  scanType,
  setScanType,
  layers,
  setLayers,
  language,
  setLanguage,
  country,
  setCountry,
  maxSeedsPerLayer,
  setMaxSeedsPerLayer,
  requestDelay,
  setRequestDelay,
  isRunning,
  onStart,
  onStop,
  languages,
  countries,
}: KeywordSearchFormProps) {
  return (
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
          <div className="flex flex-col sm:flex-row gap-2">
            <Input
              placeholder="مثال: قهوه کلدبرو"
              value={seed}
              onChange={(e) => setSeed(e.target.value)}
              disabled={isRunning}
              onKeyDown={(e) => {
                if (e.key === "Enter") onStart();
              }}
              className="flex-1"
            />
            {!isRunning ? (
              <Button
                onClick={onStart}
                disabled={!seed.trim()}
                className="bg-primary hover:bg-primary/90 w-full sm:w-auto sm:min-w-[120px]"
              >
                <Search className="w-4 h-4 ml-2" />
                شروع اسکن
              </Button>
            ) : (
              <Button
                onClick={onStop}
                variant="destructive"
                className="w-full sm:w-auto sm:min-w-[120px]"
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
              {languages.map((l) => (
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
              {countries.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Advanced settings */}
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
  );
}
