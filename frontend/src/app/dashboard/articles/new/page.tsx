"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import ArticleGenerator from "@/components/dashboard/ArticleGenerator";

/**
 * Inner component that reads ?keyword= from URL.
 * Wrapped in <Suspense> per Next.js App Router requirement
 * to prevent Vercel build errors with useSearchParams.
 */
function NewArticleContent() {
  const searchParams = useSearchParams();
  const prefillKeyword = searchParams.get("keyword") || "";
  const h2sParam = searchParams.get("h2s");
  let prefillH2s: string[] = [];
  try {
    if (h2sParam) {
      prefillH2s = JSON.parse(h2sParam);
    }
  } catch (e) {
    console.error("Failed to parse h2s param:", e);
  }

  return <ArticleGenerator initialKeyword={prefillKeyword} initialH2s={prefillH2s} />;
}

export default function NewArticlePage() {
  return (
    <Suspense fallback={<div className="flex justify-center py-20 text-muted-foreground">در حال بارگذاری...</div>}>
      <NewArticleContent />
    </Suspense>
  );
}
