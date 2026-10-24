"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Sparkles,
  LayoutList,
  AlertTriangle,
  FileText,
  Users,
  Target,
  X,
  ArrowLeft,
  CheckCircle2,
} from "lucide-react";
import { useRouter } from "next/navigation";

export interface ClusterData {
  cluster_name: string;
  pillar_keyword: string;
  suggested_h1?: string | null;
  target_audience?: string | null;
  h2_keywords: string[];
  search_intent: string;
  cannibalization_warning?: string | null;
}

interface TopicClusterCardProps {
  cluster: ClusterData;
}

function getIntentBadgeColor(intent: string) {
  const normalized = intent.toLowerCase();
  if (normalized.includes("info")) return "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300 border-blue-300 dark:border-blue-800";
  if (normalized.includes("trans")) return "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300 border-emerald-300 dark:border-emerald-800";
  if (normalized.includes("commer")) return "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300 border-purple-300 dark:border-purple-800";
  return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700";
}

export function TopicClusterCard({ cluster }: TopicClusterCardProps) {
  const router = useRouter();
  const [showBriefModal, setShowBriefModal] = useState(false);

  const defaultTopic =
    cluster.suggested_h1 ||
    `${cluster.cluster_name}: راهنمای جامع و صفر تا صد ${cluster.pillar_keyword}`;

  const handleGenerateArticle = (chosenTopic?: string) => {
    const params = new URLSearchParams();
    params.set("topic", chosenTopic || defaultTopic);
    params.set("keyword", cluster.pillar_keyword);
    if (cluster.h2_keywords.length > 0) {
      params.set("h2s", JSON.stringify(cluster.h2_keywords));
    }
    router.push(`/dashboard/articles/new?${params.toString()}`);
  };

  return (
    <>
      <Card className="flex flex-col h-full bg-card/60 backdrop-blur-sm border-border/50 hover:shadow-lg hover:border-primary/30 transition-all duration-300">
        <CardHeader className="pb-3">
          <div className="flex justify-between items-start gap-3">
            <CardTitle className="text-lg font-bold leading-tight">
              {cluster.cluster_name}
            </CardTitle>
            <Badge className={`${getIntentBadgeColor(cluster.search_intent)} whitespace-nowrap text-xs`} variant="outline">
              {cluster.search_intent}
            </Badge>
          </div>
          <CardDescription className="text-sm pt-2 flex flex-col gap-1.5">
            <span className="font-semibold text-foreground flex items-center gap-1.5">
              <Target className="w-4 h-4 text-primary" />
              کلمه محوری (Pillar): <span className="text-primary font-bold">{cluster.pillar_keyword}</span>
            </span>
            {cluster.suggested_h1 && (
              <span className="text-xs text-muted-foreground flex items-center gap-1.5 line-clamp-1">
                <FileText className="w-3.5 h-3.5 text-muted-foreground/70 shrink-0" />
                H1 پیشنهادی: {cluster.suggested_h1}
              </span>
            )}
          </CardDescription>
        </CardHeader>

        <CardContent className="flex-1">
          {cluster.cannibalization_warning && (
            <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 rounded-lg text-xs flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
              <p className="leading-relaxed">{cluster.cannibalization_warning}</p>
            </div>
          )}

          <div className="space-y-2">
            <div className="text-xs font-semibold text-muted-foreground flex items-center gap-1.5 mb-2">
              <LayoutList className="w-3.5 h-3.5" />
              زیرعنوان‌های تخصیص‌یافته ({cluster.h2_keywords.length})
            </div>
            <div className="flex flex-wrap gap-1.5">
              {cluster.h2_keywords.slice(0, 6).map((h2, idx) => (
                <Badge
                  key={idx}
                  variant="secondary"
                  className="font-normal text-xs bg-muted/60 hover:bg-muted"
                >
                  {h2}
                </Badge>
              ))}
              {cluster.h2_keywords.length > 6 && (
                <Badge variant="outline" className="text-xs text-muted-foreground">
                  +{cluster.h2_keywords.length - 6} مورد دیگر
                </Badge>
              )}
              {cluster.h2_keywords.length === 0 && (
                <span className="text-xs text-muted-foreground italic">بدون زیرعنوان تخصیص یافته</span>
              )}
            </div>
          </div>
        </CardContent>

        <CardFooter className="pt-3 border-t border-border/40 grid grid-cols-2 gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowBriefModal(true)}
            className="text-xs font-medium hover:bg-muted/80"
          >
            <FileText className="w-3.5 h-3.5 ml-1.5 text-primary" />
            شناسنامه محتوا
          </Button>

          <Button
            size="sm"
            onClick={() => handleGenerateArticle()}
            className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm text-xs font-semibold"
          >
            <Sparkles className="w-3.5 h-3.5 ml-1.5" />
            تولید مقاله AI
          </Button>
        </CardFooter>
      </Card>

      {/* ═══════ Modal: شناسنامه استراتژی محتوا (Content Brief) ═══════ */}
      {showBriefModal && (
        <div
          dir="rtl"
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-md animate-in fade-in duration-200"
          onClick={() => setShowBriefModal(false)}
        >
          <div
            className="bg-card text-card-foreground border border-border/60 shadow-2xl rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border/50 pb-4">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-primary/10 rounded-xl text-primary">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold">شناسنامه استراتژی محتوا (Content Brief)</h3>
                  <p className="text-xs text-muted-foreground">معماری و نقشه راه تولید مقاله پیش از نگارش</p>
                </div>
              </div>
              <button
                onClick={() => setShowBriefModal(false)}
                className="text-muted-foreground hover:text-foreground hover:bg-muted p-1.5 rounded-lg transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Strategic Overview Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div className="p-3 bg-muted/40 rounded-xl border border-border/40 space-y-1">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <Target className="w-3.5 h-3.5 text-primary" />
                  کلمه کلیدی محوری (Pillar)
                </span>
                <p className="text-sm font-bold text-foreground">{cluster.pillar_keyword}</p>
              </div>

              <div className="p-3 bg-muted/40 rounded-xl border border-border/40 space-y-1">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-primary" />
                  نیت جستجوی کاربر (Intent)
                </span>
                <Badge className={`${getIntentBadgeColor(cluster.search_intent)} text-xs`} variant="outline">
                  {cluster.search_intent}
                </Badge>
              </div>

              <div className="p-3 bg-muted/40 rounded-xl border border-border/40 space-y-1 sm:col-span-2">
                <span className="text-xs font-medium text-muted-foreground flex items-center gap-1.5">
                  <Users className="w-3.5 h-3.5 text-indigo-500" />
                  پرسونای مخاطب هدف (Target Persona)
                </span>
                <p className="text-xs font-medium text-foreground">
                  {cluster.target_audience || "مخاطبان هدف جستجوگر در گوگل به دنبال پاسخ جامع و عملیاتی"}
                </p>
              </div>
            </div>

            {/* Suggested H1 Title */}
            <div className="space-y-1.5 p-3.5 bg-primary/5 rounded-xl border border-primary/20">
              <span className="text-xs font-bold text-primary flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                عنوان پیشنهادی برای مقاله (H1)
              </span>
              <p className="text-sm font-bold text-foreground leading-relaxed">
                {cluster.suggested_h1 || defaultTopic}
              </p>
            </div>

            {/* H2 Outlines Checklist */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-bold">
                <span className="flex items-center gap-1.5 text-foreground">
                  <LayoutList className="w-4 h-4 text-primary" />
                  سرفصل‌ها و بخش‌های مقاله (H2 Headings)
                </span>
                <span className="text-muted-foreground">{cluster.h2_keywords.length} بخش تضمینی</span>
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {cluster.h2_keywords.map((h2, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 p-2 bg-muted/30 rounded-lg text-xs text-foreground font-medium border border-border/30"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <span>{h2}</span>
                  </div>
                ))}
                {cluster.h2_keywords.length === 0 && (
                  <p className="text-xs text-muted-foreground italic p-2">
                    زیرعنوانی تعریف نشده است. مدل در حین نگارش به طور خودکار عناوین سئو تولید خواهد کرد.
                  </p>
                )}
              </div>
            </div>

            {/* Cannibalization Warning if present */}
            {cluster.cannibalization_warning && (
              <div className="p-3 bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-200 rounded-xl text-xs flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0 text-amber-600 dark:text-amber-400" />
                <p className="leading-relaxed">{cluster.cannibalization_warning}</p>
              </div>
            )}

            {/* Modal Actions */}
            <div className="pt-3 border-t border-border/50 flex items-center justify-end gap-2.5">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setShowBriefModal(false)}
                className="text-xs"
              >
                بستن
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  setShowBriefModal(false);
                  handleGenerateArticle(cluster.suggested_h1 || defaultTopic);
                }}
                className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-md text-xs font-bold"
              >
                <Sparkles className="w-3.5 h-3.5 ml-1.5" />
                تولید مقاله با این شناسنامه
                <ArrowLeft className="w-3.5 h-3.5 mr-1" />
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
