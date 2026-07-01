"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Plus, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getArticles, approveArticle, publishArticle, type Article } from "@/lib/api";

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getArticles()
      .then(setArticles)
      .catch((err) => {
        setError("خطا در دریافت لیست مقالات. لطفا دوباره تلاش کنید.");
        console.error(err);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleApprove = async (id: number) => {
    try {
      setError("");
      await approveArticle(id);
      setArticles(articles.map(a => a.id === id ? { ...a, status: 'approved' } : a));
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string | string[] } } };
      const msg = axiosError.response?.data?.detail || "خطا در تایید مقاله";
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  const handlePublish = async (id: number) => {
    try {
      setError("");
      await publishArticle(id);
      setArticles(articles.map(a => a.id === id ? { ...a, status: 'published' } : a));
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string | string[] } } };
      const msg = axiosError.response?.data?.detail || "خطا در انتشار مقاله";
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "published":
        return <span className="px-2 py-1 bg-green-500/10 text-green-500 rounded-md text-xs font-medium">منتشر شده</span>;
      case "approved":
        return <span className="px-2 py-1 bg-blue-500/10 text-blue-500 rounded-md text-xs font-medium">تایید شده</span>;
      case "pending_approval":
        return <span className="px-2 py-1 bg-yellow-500/10 text-yellow-500 rounded-md text-xs font-medium">در انتظار تایید</span>;
      case "draft":
        return <span className="px-2 py-1 bg-primary/10 text-primary rounded-md text-xs font-medium">پیش‌نویس</span>;
      default:
        return <span className="px-2 py-1 bg-gray-500/10 text-gray-500 rounded-md text-xs font-medium">{status}</span>;
    }
  };

  return (
    <div dir="rtl" className="mx-auto max-w-5xl space-y-8 animate-fade-in-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-8">
        <div>
          <h2 className="text-3xl font-extrabold text-foreground tracking-tight">لیست مقالات</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            مدیریت و مشاهده تمامی مقالات تولید شده توسط هوش مصنوعی.
          </p>
        </div>
        <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-md">
          <Link href="/dashboard/articles/new">
            <Plus className="ml-2 h-4 w-4" />
            تولید مقاله جدید
          </Link>
        </Button>
      </div>

      {error && (
        <div className="p-4 bg-destructive/10 text-destructive rounded-xl border border-destructive/20 text-sm">
          {error}
        </div>
      )}

      <div className="bg-background/50 backdrop-blur-sm border border-border/50 rounded-2xl overflow-hidden shadow-sm">
        {loading ? (
          <div className="flex items-center justify-center p-12 text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin" />
            <span className="mr-3">در حال بارگذاری...</span>
          </div>
        ) : articles.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-16 text-center">
            <div className="bg-primary/10 p-4 rounded-full mb-4">
              <FileText className="h-8 w-8 text-primary" />
            </div>
            <h3 className="text-lg font-semibold text-foreground mb-2">هنوز مقاله‌ای ندارید</h3>
            <p className="text-muted-foreground text-sm max-w-sm">
              اولین مقاله سئومحور خود را با قدرت هوش مصنوعی در چند ثانیه بسازید.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-right">
              <thead className="bg-muted/30 text-muted-foreground border-b border-border/50">
                <tr>
                  <th className="px-6 py-4 font-semibold w-1/2">عنوان مقاله</th>
                  <th className="px-6 py-4 font-semibold">کلمه کلیدی</th>
                  <th className="px-6 py-4 font-semibold">امتیاز سئو</th>
                  <th className="px-6 py-4 font-semibold">وضعیت</th>
                  <th className="px-6 py-4 font-semibold">تاریخ ایجاد</th>
                  <th className="px-6 py-4 font-semibold text-center">عملیات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {articles.map((article) => (
                  <tr key={article.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-semibold text-foreground truncate max-w-[200px] md:max-w-[400px]">
                        {article.title}
                      </p>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground">
                      {article.focus_keyword}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className={`font-bold ${
                          article.seo_score >= 80 ? 'text-green-500' : 
                          article.seo_score >= 50 ? 'text-yellow-500' : 'text-red-500'
                        }`}>
                          {article.seo_score}
                        </span>
                        <span className="text-xs text-muted-foreground">/ 100</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(article.status)}
                    </td>
                    <td className="px-6 py-4 text-muted-foreground text-xs">
                      {new Intl.DateTimeFormat("fa-IR", { dateStyle: "short", timeStyle: "short" }).format(new Date(article.created_at))}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center justify-center gap-2">
                        <Button variant="outline" size="sm" onClick={() => alert("بخش ویرایشگر مجزا در فازهای بعدی اضافه خواهد شد.")}>مشاهده</Button>
                        {article.status === 'pending_approval' && (
                           <Button size="sm" className="bg-green-600 hover:bg-green-500" onClick={() => handleApprove(article.id)}>تایید</Button>
                        )}
                        {article.status === 'approved' && (
                           <Button size="sm" className="bg-blue-600 hover:bg-blue-500" onClick={() => handlePublish(article.id)}>انتشار</Button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
