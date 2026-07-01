"use client";

import { useEffect, useState, use } from "react";
import { Loader2, Save, Wand2, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  getArticle,
  updateArticle,
  improveArticlePreview,
  assignEditors,
  getMe,
  getUsers,
  type Article,
  type User,
} from "@/lib/api";

export default function ArticleDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const resolvedParams = use(params);
  const articleId = parseInt(resolvedParams.id, 10);

  const [article, setArticle] = useState<Article | null>(null);
  const [me, setMe] = useState<User | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [contentHtml, setContentHtml] = useState("");
  const [title, setTitle] = useState("");

  // AI Improve State
  const [showAiModal, setShowAiModal] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [model, setModel] = useState("openai/gpt-4o-mini");
  const [improving, setImproving] = useState(false);
  const [previewData, setPreviewData] = useState<{ new_html: string; new_seo_score: number; old_seo_score: number } | null>(null);

  // Assign Editors State
  const [selectedEditors, setSelectedEditors] = useState<number[]>([]);

  useEffect(() => {
    Promise.all([
      getMe(),
      getArticle(articleId),
      getUsers().catch(() => [])
    ])
      .then(([meData, articleData, usersData]) => {
        setMe(meData);
        setArticle(articleData);
        setTitle(articleData.title);
        setContentHtml(articleData.content_html);
        setSelectedEditors(articleData.assigned_editors.map(e => e.id));
        setUsers(usersData.filter(u => u.role === "editor" || u.role === "admin"));
      })
      .catch((err) => {
        setError("خطا در بارگذاری مقاله.");
        console.error(err);
      })
      .finally(() => setLoading(false));
  }, [articleId]);

  const handleSave = async () => {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await updateArticle(articleId, { title, content_html: contentHtml });
      
      if (me?.role === "admin") {
        await assignEditors(articleId, selectedEditors);
      }
      
      setMessage("مقاله با موفقیت ذخیره شد.");
    } catch {
      setError("خطا در ذخیره مقاله.");
    } finally {
      setSaving(false);
    }
  };

  const handleAiImprovePreview = async () => {
    setImproving(true);
    setPreviewData(null);
    try {
      const data = await improveArticlePreview(articleId, instruction, model);
      setPreviewData(data);
    } catch (err: unknown) {
      const axiosError = err as { response?: { status?: number } };
      if (axiosError.response?.status === 429) {
        alert("سقف درخواست‌های روزانه پر شده است. لطفاً فردا تلاش کنید.");
      } else {
        alert("خطا در ارتباط با هوش مصنوعی.");
      }
    } finally {
      setImproving(false);
    }
  };

  const handleApplyPreview = () => {
    if (previewData) {
      setContentHtml(previewData.new_html);
      setShowAiModal(false);
      setPreviewData(null);
      setMessage("تغییرات هوش مصنوعی اعمال شد. برای نهایی شدن روی ذخیره کلیک کنید.");
    }
  };

  const toggleEditorSelection = (id: number) => {
    setSelectedEditors(prev => 
      prev.includes(id) ? prev.filter(e => e !== id) : [...prev, id]
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center py-20 text-muted-foreground">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  if (!article) {
    return <div className="text-center py-20">مقاله یافت نشد.</div>;
  }

  return (
    <div dir="rtl" className="mx-auto max-w-5xl space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h2 className="text-2xl font-bold">ویرایش مقاله: {article.title}</h2>
          <p className="text-muted-foreground mt-1">کلمه کلیدی: {article.focus_keyword} | امتیاز سئو: {article.seo_score}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setShowAiModal(true)} className="bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border-indigo-200">
            <Wand2 className="w-4 h-4 ml-2" />
            بهبود با هوش مصنوعی
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            {saving ? <Loader2 className="w-4 h-4 animate-spin ml-2" /> : <Save className="w-4 h-4 ml-2" />}
            ذخیره تغییرات
          </Button>
        </div>
      </div>

      {error && <div className="p-4 bg-red-100 text-red-800 rounded">{error}</div>}
      {message && <div className="p-4 bg-green-100 text-green-800 rounded">{message}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-2 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>محتوای مقاله</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>عنوان مقاله</Label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>ویرایشگر HTML</Label>
                <textarea
                  className="w-full h-[500px] p-4 border rounded-md font-mono text-sm text-left"
                  dir="ltr"
                  value={contentHtml}
                  onChange={(e) => setContentHtml(e.target.value)}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>پیش‌نمایش زنده</CardTitle>
            </CardHeader>
            <CardContent>
              <div 
                className="prose prose-sm max-w-none border rounded-md p-4 bg-background max-h-[500px] overflow-y-auto"
                dangerouslySetInnerHTML={{ __html: contentHtml }}
              />
            </CardContent>
          </Card>

          {me?.role === "admin" && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Users className="w-4 h-4 ml-2" />
                  تخصیص ویراستاران
                </CardTitle>
                <CardDescription>ویراستاران مجاز به دسترسی را انتخاب کنید.</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-60 overflow-y-auto border p-2 rounded-md">
                  {users.map(u => (
                    <label key={u.id} className="flex items-center space-x-2 space-x-reverse cursor-pointer hover:bg-muted p-1 rounded">
                      <input 
                        type="checkbox" 
                        checked={selectedEditors.includes(u.id)}
                        onChange={() => toggleEditorSelection(u.id)}
                        className="w-4 h-4"
                      />
                      <span>{u.username} ({u.role})</span>
                    </label>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* AI Improve Modal */}
      {showAiModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-background w-full max-w-3xl rounded-xl shadow-2xl p-6 space-y-6 max-h-[90vh] overflow-y-auto">
            <h3 className="text-xl font-bold flex items-center">
              <Wand2 className="w-5 h-5 ml-2 text-indigo-500" />
              بهبود تعاملی مقاله با هوش مصنوعی
            </h3>
            
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>دستورالعمل ویرایش (اختیاری)</Label>
                <textarea 
                  className="w-full p-3 border rounded-md"
                  placeholder="مثلاً: لحن مقاله را رسمی‌تر کن و دو پاراگراف اول را خلاصه کن..."
                  rows={3}
                  value={instruction}
                  onChange={(e) => setInstruction(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">اگر خالی بگذارید، هوش مصنوعی مقاله را برای سئو و روانی به صورت عمومی بازبینی می‌کند.</p>
              </div>

              <div className="space-y-2">
                <Label>مدل هوش مصنوعی</Label>
                <select className="w-full border p-2 rounded-md" value={model} onChange={(e) => setModel(e.target.value)}>
                  <option value="openai/gpt-4o-mini">GPT-4o Mini (سریع و اقتصادی)</option>
                  <option value="openai/gpt-4o">GPT-4o (قدرتمند و دقیق)</option>
                  <option value="groq/llama-3.3-70b-versatile">Llama 3.3 70B (ارزان)</option>
                </select>
              </div>

              {!previewData ? (
                <Button onClick={handleAiImprovePreview} disabled={improving} className="w-full bg-indigo-600 hover:bg-indigo-500">
                  {improving ? <Loader2 className="w-5 h-5 animate-spin ml-2" /> : <Wand2 className="w-5 h-5 ml-2" />}
                  {improving ? "در حال بازبینی مقاله و پردازش هوش مصنوعی..." : "شروع بازبینی و مشاهده پیش‌نمایش"}
                </Button>
              ) : (
                <div className="space-y-4 border-t pt-4">
                  <div className="flex justify-between items-center bg-muted/50 p-4 rounded-lg">
                    <div className="text-center">
                      <p className="text-sm text-muted-foreground">امتیاز سئو قبلی</p>
                      <p className="text-2xl font-bold">{previewData.old_seo_score}</p>
                    </div>
                    <div className="text-indigo-500">
                      →
                    </div>
                    <div className="text-center">
                      <p className="text-sm text-muted-foreground">امتیاز سئو جدید</p>
                      <p className={`text-2xl font-bold ${previewData.new_seo_score >= previewData.old_seo_score ? 'text-green-500' : 'text-red-500'}`}>
                        {previewData.new_seo_score}
                      </p>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label>پیش‌نمایش HTML تغییر یافته</Label>
                    <div 
                      className="prose prose-sm border p-4 max-h-60 overflow-y-auto rounded-md bg-muted/30"
                      dangerouslySetInnerHTML={{ __html: previewData.new_html }}
                    />
                  </div>

                  <div className="flex gap-2 justify-end">
                    <Button variant="outline" onClick={() => setPreviewData(null)}>لغو و تلاش مجدد</Button>
                    <Button onClick={handleApplyPreview} className="bg-green-600 hover:bg-green-500">تایید و جایگزینی</Button>
                  </div>
                </div>
              )}
            </div>
            
            <div className="flex justify-end pt-4 border-t">
              <Button variant="ghost" onClick={() => setShowAiModal(false)}>بستن</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
