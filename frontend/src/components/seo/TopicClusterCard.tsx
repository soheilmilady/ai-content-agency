"use client";

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
import { Sparkles, LayoutList, AlertTriangle } from "lucide-react";
import { useRouter } from "next/navigation";

export interface ClusterData {
  cluster_name: string;
  pillar_keyword: string;
  h2_keywords: string[];
  search_intent: string;
  cannibalization_warning?: string | null;
}

interface TopicClusterCardProps {
  cluster: ClusterData;
}

function getIntentBadgeColor(intent: string) {
  const normalized = intent.toLowerCase();
  if (normalized.includes("info")) return "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300";
  if (normalized.includes("trans")) return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300";
  if (normalized.includes("commer")) return "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300";
  return "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-300";
}

export function TopicClusterCard({ cluster }: TopicClusterCardProps) {
  const router = useRouter();

  const handleGenerateArticle = () => {
    const params = new URLSearchParams();
    params.set("keyword", cluster.pillar_keyword);
    if (cluster.h2_keywords.length > 0) {
      params.set("h2s", JSON.stringify(cluster.h2_keywords));
    }
    router.push(`/dashboard/articles/new?${params.toString()}`);
  };

  return (
    <Card className="flex flex-col h-full bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm border-slate-200 dark:border-slate-800 hover:shadow-md transition-all duration-300">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start gap-4">
          <CardTitle className="text-xl font-bold leading-tight">
            {cluster.cluster_name}
          </CardTitle>
          <Badge className={`${getIntentBadgeColor(cluster.search_intent)} whitespace-nowrap`} variant="outline">
            {cluster.search_intent}
          </Badge>
        </div>
        <CardDescription className="text-sm pt-2 flex flex-col gap-1">
          <span className="font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
            <span className="text-primary text-lg">📌</span>
            تیتر اصلی (Pillar): {cluster.pillar_keyword}
          </span>
        </CardDescription>
      </CardHeader>
      
      <CardContent className="flex-1">
        {cluster.cannibalization_warning && (
          <div className="mb-4 p-3 bg-amber-50 dark:bg-amber-950/30 text-amber-800 dark:text-amber-200 rounded-lg text-sm flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
            <p className="leading-relaxed">{cluster.cannibalization_warning}</p>
          </div>
        )}
        
        <div className="space-y-2">
          <div className="text-sm font-medium text-slate-600 dark:text-slate-400 flex items-center gap-2 mb-3">
            <LayoutList className="w-4 h-4" />
            زیرعنوان‌های مقاله (H2)
          </div>
          <div className="flex flex-wrap gap-2">
            {cluster.h2_keywords.map((h2, idx) => (
              <Badge key={idx} variant="secondary" className="font-normal bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700">
                {h2}
              </Badge>
            ))}
            {cluster.h2_keywords.length === 0 && (
              <span className="text-sm text-slate-400 italic">بدون زیرعنوان تخصیص یافته</span>
            )}
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-4 border-t border-slate-100 dark:border-slate-800">
        <Button 
          onClick={handleGenerateArticle}
          className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-sm transition-all"
        >
          <Sparkles className="w-4 h-4 ml-2" />
          تولید مقاله AI با این ساختار
        </Button>
      </CardFooter>
    </Card>
  );
}
