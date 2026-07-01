"use client";

import { useState } from "react";
import Cookies from "js-cookie";
import { Loader2, Sparkles } from "lucide-react";
import DOMPurify from "dompurify";

import TipTapEditor from "@/components/editor/TipTapEditor";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { publishArticle, updateArticle } from "@/lib/api";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const AI_MODELS = [
  {
    value: "llama-3.3-70b-versatile",
    label: "Ultra Quality — Llama 3.3 70B",
    description: "بهترین کیفیت برای مقالات مهم",
  },
  {
    value: "llama-3.1-8b-instant",
    label: "Standard — Llama 3.1 8B",
    description: "سریع و مناسب بلاگ روزانه",
  },
  {
    value: "meta-llama/llama-4-scout-17b-16e-instruct",
    label: "Economy — Llama 4 Scout 17B",
    description: "مدل جایگزین اقتصادی",
  },
];

type StreamEvent = {
  step?: string;
  message?: string;
  token?: string;
  article_id?: number;
  seo_score?: number;
  meta_description?: string;
  title?: string;
};

function seoBadgeClass(score: number) {
  if (score > 85)
    return "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-950 dark:text-green-300";
  if (score > 70)
    return "bg-yellow-100 text-yellow-800 hover:bg-yellow-100 dark:bg-yellow-950 dark:text-yellow-300";
  return "bg-red-100 text-red-800 hover:bg-red-100 dark:bg-red-950 dark:text-red-300";
}

function parseSseChunk(buffer: string): {
  events: StreamEvent[];
  remainder: string;
} {
  const events: StreamEvent[] = [];
  const parts = buffer.split("\n\n");
  const remainder = parts.pop() || "";

  for (const part of parts) {
    const line = part.trim();
    if (!line.startsWith("data: ")) continue;
    try {
      events.push(JSON.parse(line.slice(6)) as StreamEvent);
    } catch {
      // ignore malformed chunks
    }
  }

  return { events, remainder };
}

export default function ArticleGenerator() {
  const [topic, setTopic] = useState("");
  const [keyword, setKeyword] = useState("");
  const [selectedModel, setSelectedModel] = useState(AI_MODELS[0].value);

  const [generating, setGenerating] = useState(false);
  const [stepMessage, setStepMessage] = useState("");
  const [streamedContent, setStreamedContent] = useState("");
  const [showPreview, setShowPreview] = useState(false);

  const [articleId, setArticleId] = useState<number | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [metaDescription, setMetaDescription] = useState("");
  const [seoScore, setSeoScore] = useState<number | null>(null);

  const [saving, setSaving] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const [error, setError] = useState("");

  async function handleGenerate() {
    if (!topic.trim() || !keyword.trim()) {
      setError("لطفاً موضوع و کلمه کلیدی را وارد کنید.");
      return;
    }

    const token = Cookies.get("auth_token");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    setError("");
    setActionMessage("");
    setGenerating(true);
    setShowPreview(false);
    setStreamedContent("");
    setStepMessage("در حال آماده‌سازی...");
    setArticleId(null);
    setSeoScore(null);
    setMetaDescription("");

    try {
      const response = await fetch(`${API_URL}/articles/generate-stream`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          topic,
          keyword,
          llm_model: selectedModel,
        }),
      });

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error("سقف درخواست‌های روزانه پر شده است. لطفاً فردا تلاش کنید.");
        }
        throw new Error("خطا در شروع تولید محتوا");
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("پاسخ استریم در دسترس نیست");
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let accumulated = "";
      let streamError = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const { events, remainder } = parseSseChunk(buffer);
        buffer = remainder;

        for (const event of events) {
          if (event.step === "error") {
            streamError = event.message || "خطای ناشناخته در تولید محتوا";
            continue;
          }

          if (event.message) {
            setStepMessage(event.message);
          }

          if (event.token) {
            accumulated += event.token;
            setStreamedContent(accumulated);
          }

          if (event.step === "done") {
            setArticleId(event.article_id ?? null);
            setSeoScore(event.seo_score ?? null);
            setMetaDescription(event.meta_description ?? "");
            setEditorContent(accumulated);
            setShowPreview(true);
            setStepMessage("تولید محتوا با موفقیت انجام شد.");
          }
        }
      }

      if (streamError) {
        throw new Error(streamError);
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "تولید محتوا با خطا مواجه شد. لطفاً دوباره تلاش کنید."
      );
    } finally {
      setGenerating(false);
    }
  }

  async function handleSaveDraft() {
    if (!articleId) return;

    setSaving(true);
    setActionMessage("");
    setError("");

    try {
      await updateArticle(articleId, {
        content_html: editorContent,
        status: "draft",
      });
      setActionMessage("پیش‌نویس با موفقیت ذخیره شد.");
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string | string[] } } };
      const msg = axiosError.response?.data?.detail || "ذخیره پیش‌نویس با خطا مواجه شد.";
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setSaving(false);
    }
  }

  async function handlePublish() {
    if (!articleId) return;

    setPublishing(true);
    setActionMessage("");
    setError("");

    try {
      await updateArticle(articleId, { content_html: editorContent });
      await publishArticle(articleId);
      setActionMessage("مقاله با موفقیت در وردپرس منتشر شد.");
    } catch (err) {
      const axiosError = err as { response?: { data?: { detail?: string | string[] } } };
      const msg = axiosError.response?.data?.detail || "انتشار مقاله با خطا مواجه شد. تنظیمات وردپرس را بررسی کنید.";
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setPublishing(false);
    }
  }

  return (
    <div dir="rtl" className="mx-auto max-w-5xl space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground">تولید مقاله جدید</h2>
        <p className="mt-1 text-muted-foreground">
          موضوع و کلمه کلیدی را وارد کنید تا مقاله سئو محور تولید شود.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-indigo-600" />
            فرم تولید محتوا
          </CardTitle>
          <CardDescription>
            مدل هوش مصنوعی را بر اساس کیفیت و بودجه انتخاب کنید.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-5 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="topic">موضوع مقاله</Label>
              <Input
                id="topic"
                placeholder="مثال: راهنمای کامل سئو محتوا"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                disabled={generating}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="keyword">کلمه کلیدی اصلی</Label>
              <Input
                id="keyword"
                placeholder="مثال: سئو محتوا"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                disabled={generating}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label>مدل هوش مصنوعی</Label>
            <Select
              value={selectedModel}
              onValueChange={setSelectedModel}
              disabled={generating}
            >
              <SelectTrigger>
                <SelectValue placeholder="انتخاب مدل" />
              </SelectTrigger>
              <SelectContent>
                {AI_MODELS.map((model) => (
                  <SelectItem key={model.value} value={model.value}>
                    <span className="font-medium">{model.label}</span>
                    <span className="mr-2 text-muted-foreground">
                      ({model.description})
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {error && (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/60 dark:text-red-300">
              {error}
            </p>
          )}

          <Button
            onClick={handleGenerate}
            disabled={generating}
            className="bg-indigo-600 hover:bg-indigo-500"
          >
            {generating ? (
              <>
                <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                در حال تولید...
              </>
            ) : (
              "شروع تولید محتوا"
            )}
          </Button>
        </CardContent>
      </Card>

      {generating && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">وضعیت تولید</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
              <p className="text-sm font-medium text-foreground">{stepMessage}</p>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div className="h-full animate-pulse rounded-full bg-indigo-500" />
            </div>
            {streamedContent && (
              <div className="max-h-80 overflow-y-auto rounded-lg border border-border bg-muted p-4">
                <div
                  className="tiptap text-right"
                  dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(streamedContent) }}
                />
                <span className="mr-1 inline-block h-5 w-0.5 animate-pulse bg-indigo-600" />
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {showPreview && (
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <CardTitle className="text-lg">پیش‌نمایش و ویرایش</CardTitle>
                <CardDescription className="mt-1">
                  محتوای تولید شده را بررسی و در صورت نیاز ویرایش کنید.
                </CardDescription>
              </div>
              {seoScore !== null && (
                <Badge className={seoBadgeClass(seoScore)}>
                  امتیاز سئو: {seoScore}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-5">
            {metaDescription && (
              <div className="rounded-lg border border-border bg-muted p-4">
                <p className="mb-1 text-sm font-medium text-foreground">
                  توضیحات متا
                </p>
                <p className="text-sm leading-7 text-muted-foreground">
                  {metaDescription}
                </p>
              </div>
            )}

            <TipTapEditor
              content={editorContent}
              onChange={setEditorContent}
              editable
            />

            {actionMessage && (
              <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800 dark:border-green-900 dark:bg-green-950/60 dark:text-green-300">
                {actionMessage}
              </p>
            )}

            <div className="flex flex-wrap gap-3">
              <Button
                variant="outline"
                onClick={handleSaveDraft}
                disabled={saving || publishing}
              >
                {saving ? (
                  <>
                    <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                    در حال ذخیره...
                  </>
                ) : (
                  "ذخیره پیش‌نویس"
                )}
              </Button>
              <Button
                onClick={handlePublish}
                disabled={saving || publishing}
                className="bg-indigo-600 hover:bg-indigo-500"
              >
                {publishing ? (
                  <>
                    <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                    در حال انتشار...
                  </>
                ) : (
                  "تأیید و انتشار در وردپرس"
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
