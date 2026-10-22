"use client";

import { Copy, ExternalLink, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { KeywordEntry } from "@/hooks/useGoogleSuggest";

export interface KeywordResultsTableProps {
  paginatedResults: KeywordEntry[];
  translations: Record<string, string>;
  activePage: number;
  pageSize: number;
  totalPages: number;
  totalFilteredCount: number;
  onPageChange: (page: number) => void;
  onCopy: (keyword: string, index: number) => void;
  copiedIndex: number | null;
  onOpenGoogle: (keyword: string) => void;
  onGenerateArticle: (keyword: string) => void;
}

export function KeywordResultsTable({
  paginatedResults,
  translations,
  activePage,
  pageSize,
  totalPages,
  totalFilteredCount,
  onPageChange,
  onCopy,
  copiedIndex,
  onOpenGoogle,
  onGenerateArticle,
}: KeywordResultsTableProps) {
  const hasTranslations = Object.keys(translations).length > 0;

  return (
    <>
      <div className="max-h-[600px] overflow-y-auto rounded-lg border border-border/30">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-muted/80 backdrop-blur-sm z-10">
            <tr className="text-xs text-muted-foreground">
              <th className="text-right py-2.5 px-3 font-semibold">#</th>
              <th className="text-right py-2.5 px-3 font-semibold">کلمه کلیدی</th>
              {hasTranslations && (
                <th className="text-right py-2.5 px-3 font-semibold">ترجمه فارسی</th>
              )}
              <th className="text-center py-2.5 px-3 font-semibold">فرکانس</th>
              <th className="text-center py-2.5 px-3 font-semibold">لایه</th>
              <th className="text-center py-2.5 px-3 font-semibold">نوع</th>
              <th className="text-center py-2.5 px-3 font-semibold">اقدام</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/20">
            {paginatedResults.map((entry, index) => {
              const itemNumber = (activePage - 1) * pageSize + index + 1;
              const wordCount = entry.keyword.split(/\s+/).length;
              const isLongTail = wordCount >= 4;
              return (
                <tr
                  key={entry.keyword}
                  className="hover:bg-muted/20 transition-colors"
                >
                  <td className="py-2 px-3 text-muted-foreground text-xs tabular-nums">
                    {itemNumber}
                  </td>
                  <td className="py-2 px-3 font-medium" dir="auto">
                    {entry.keyword}
                  </td>
                  {hasTranslations && (
                    <td
                      className="py-2 px-3 text-muted-foreground text-xs"
                      dir="rtl"
                    >
                      {translations[entry.keyword] || "—"}
                    </td>
                  )}
                  <td className="py-2 px-3 text-center">
                    <Badge variant="secondary" className="tabular-nums text-xs">
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
                        onClick={() => onCopy(entry.keyword, itemNumber - 1)}
                        className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
                      >
                        {copiedIndex === itemNumber - 1 ? (
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
                        onClick={() => onOpenGoogle(entry.keyword)}
                        className="p-1.5 rounded-md hover:bg-muted/50 transition-colors text-muted-foreground hover:text-foreground"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>

                      {/* Magic Bridge: Generate AI Article */}
                      <button
                        type="button"
                        title="✨ تولید مقاله AI"
                        onClick={() => onGenerateArticle(entry.keyword)}
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

      {/* Pagination Bar */}
      {totalPages > 1 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 px-4 py-3 border border-border/30 bg-muted/10 text-xs mt-3 rounded-lg">
          <div className="text-muted-foreground">
            نمایش {(activePage - 1) * pageSize + 1} تا{" "}
            {Math.min(activePage * pageSize, totalFilteredCount)} از{" "}
            {totalFilteredCount} کلمه
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={activePage <= 1}
              onClick={() => onPageChange(Math.max(1, activePage - 1))}
              className="h-8 text-xs"
            >
              قبلی
            </Button>
            <span className="tabular-nums font-semibold px-2">
              صفحه {activePage} از {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={activePage >= totalPages}
              onClick={() => onPageChange(Math.min(totalPages, activePage + 1))}
              className="h-8 text-xs"
            >
              بعدی
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
