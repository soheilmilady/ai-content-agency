"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText, Plus, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { getArticles, approveArticle, publishArticle, deleteArticle, getMe, type Article, type User } from "@/lib/api";

const formatDateTime = (dateString?: string | null) => {
  if (!dateString) return "-";
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return "-";
  return new Intl.DateTimeFormat("fa-IR", { dateStyle: "short", timeStyle: "short" }).format(date);
};

export default function ArticlesPage() {
  const [articles, setArticles] = useState<Article[]>([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<number | null>(null);
  const [deleteTargetId, setDeleteTargetId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [me, setMe] = useState<User | null>(null);

  useEffect(() => {
    getMe().then(setMe).catch(() => {});
    loadArticles();
  }, []);

  const loadArticles = () => {
    setLoading(true);
    getArticles()
      .then(setArticles)
      .catch((err) => {
        setError("خطا در دریافت لیست مقالات. لطفا دوباره تلاش کنید.");
        console.error(err);
      })
      .finally(() => setLoading(false));
  };

  const handleApprove = async (id: number) => {
    if (processingId) return;
    setProcessingId(id);
    try {
      setError("");
      await approveArticle(id);
      setArticles(articles.map(a => a.id === id ? { ...a, status: 'approved' } : a));
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string | string[] } } };
      const msg = axiosError.response?.data?.detail || "خطا در تایید مقاله";
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setProcessingId(null);
    }
  };

  const handlePublish = async (id: number) => {
    if (processingId) return;
    setProcessingId(id);
    try {
      setError("");
      await publishArticle(id);
      setArticles(articles.map(a => a.id === id ? { ...a, status: 'published' } : a));
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string | string[] } } };
      const msg = axiosError.response?.data?.detail || "خطا در انتشار مقاله";
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setProcessingId(null);
    }
  };

  const confirmDelete = async () => {
    if (!deleteTargetId || processingId) return;
    const id = deleteTargetId;
    setProcessingId(id);
    try {
      setError("");
      await deleteArticle(id);
      setArticles(articles.filter(a => a.id !== id));
      setDeleteTargetId(null);
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string | string[] } } };
      const msg = axiosError.response?.data?.detail || "خطا در حذف مقاله";
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setProcessingId(null);
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
                  <th className="px-6 py-4 font-semibold w-1/4">عنوان مقاله</th>
                  <th className="px-6 py-4 font-semibold">نویسنده</th>
                  <th className="px-6 py-4 font-semibold">تغییر توسط</th>
                  <th className="px-6 py-4 font-semibold">کلمه کلیدی</th>
                  <th className="px-6 py-4 font-semibold">امتیاز سئو</th>
                  <th className="px-6 py-4 font-semibold">وضعیت</th>
                  <th className="px-6 py-4 font-semibold">تاریخ آپدیت</th>
                  <th className="px-6 py-4 font-semibold text-center">عملیات</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {articles.map((article) => (
                  <tr key={article.id} className="hover:bg-muted/20 transition-colors">
                    <td className="px-6 py-4">
                      <p className="font-semibold text-foreground truncate max-w-[150px]">
                        {article.title}
                      </p>
                    </td>
                    <td className="px-6 py-4 text-muted-foreground text-sm">
                      {article.author.username}
                    </td>
                    <td className="px-6 py-4 text-muted-foreground text-sm text-center">
                      {article.last_modified_by ? article.last_modified_by.username : "-"}
                    </td>
                    <td className="px-6 py-4 text-muted-foreground text-sm">
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
                    <td className="px-6 py-4 text-muted-foreground text-xs text-center">
                      {formatDateTime(article.updated_at)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap items-center justify-center gap-2">
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/dashboard/articles/${article.id}`}>
                            {me?.role === "admin" || article.author.id === me?.id || (me?.role === "editor" && article.assigned_editors.some(e => e.id === me?.id))
                              ? "مشاهده / ویرایش"
                              : "مشاهده"
                            }
                          </Link>
                        </Button>
                        
                        {(me?.role === "admin" || me?.role === "editor") && article.status === 'pending_approval' && (
                           <Button 
                             size="sm" 
                             className="bg-green-600 hover:bg-green-500" 
                             disabled={processingId === article.id}
                             onClick={() => handleApprove(article.id)}
                           >
                             {processingId === article.id ? <Loader2 className="w-4 h-4 animate-spin" /> : "تایید"}
                           </Button>
                        )}
                        {(me?.role === "admin" || me?.can_publish) && article.status === 'approved' && (
                           <Button 
                             size="sm" 
                             className="bg-blue-600 hover:bg-blue-500" 
                             disabled={processingId === article.id}
                             onClick={() => handlePublish(article.id)}
                           >
                             {processingId === article.id ? <Loader2 className="w-4 h-4 animate-spin" /> : "انتشار"}
                           </Button>
                        )}
                        {(me?.role === "admin" || article.author.id === me?.id || (me?.role === "editor" && article.assigned_editors.some(e => e.id === me?.id))) && (
                           <Button 
                             size="sm" 
                             variant="destructive" 
                             disabled={processingId === article.id}
                             onClick={() => setDeleteTargetId(article.id)}
                           >
                             {processingId === article.id ? <Loader2 className="w-4 h-4 animate-spin" /> : "حذف"}
                           </Button>
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

      {/* مودال تأیید حذف شیشه‌ای مدرن */}
      {deleteTargetId !== null && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm p-4 animate-fade-in">
          <div className="w-full max-w-md rounded-2xl border border-border/50 bg-card p-6 shadow-2xl space-y-4">
            <h3 className="text-lg font-bold text-foreground">تأیید حذف مقاله</h3>
            <p className="text-sm text-muted-foreground">
              آیا از حذف این مقاله اطمینان دارید؟ این عملیات غیرقابل بازگشت است.
            </p>
            <div className="flex justify-end gap-3 pt-2">
              <Button
                variant="outline"
                disabled={processingId !== null}
                onClick={() => setDeleteTargetId(null)}
              >
                انصراف
              </Button>
              <Button
                variant="destructive"
                disabled={processingId !== null}
                onClick={confirmDelete}
              >
                {processingId !== null ? <Loader2 className="w-4 h-4 animate-spin ml-2" /> : null}
                حذف مقاله
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
