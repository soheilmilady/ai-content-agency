"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { UserCircle, Users, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { getMe, type User } from "@/lib/api";

export default function DashboardPage() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    getMe().then(setUser).catch(() => {});
  }, []);

  return (
    <div dir="rtl" className="mx-auto max-w-5xl space-y-8 animate-fade-in-up">
      <div className="mb-10">
        <h2 className="text-3xl font-extrabold text-foreground tracking-tight">داشبورد کاربری</h2>
        <p className="mt-2 text-base text-muted-foreground">
          به پلتفرم محتوای هوشمند <span className="font-semibold text-primary">AI Content Agency</span> خوش آمدید. جادوی هوش مصنوعی از اینجا شروع می‌شود.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {/* کارت اصلی با تمایز نئونی */}
        <Card className="glass-card relative overflow-hidden border-primary/20 bg-primary/5">
          <div className="absolute top-0 right-0 w-32 h-32 bg-primary/10 rounded-full blur-3xl -mr-10 -mt-10 pointer-events-none"></div>
          <CardHeader className="relative z-10">
            <CardTitle className="flex items-center gap-2 text-xl text-foreground">
              <Sparkles className="h-6 w-6 text-primary animate-pulse-glow" />
              تولید مقاله AI
            </CardTitle>
            <CardDescription className="text-muted-foreground/80 mt-2">
              یک کلیک تا خلق یک مقالهٔ سئومحور، مستند و خیره‌کننده فاصله دارید.
            </CardDescription>
          </CardHeader>
          <CardContent className="relative z-10 pt-4">
            <Button asChild className="w-full bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg shadow-primary/25 transition-all">
              <Link href="/dashboard/articles/new">شروع تولید محتوا</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg text-foreground">
              <UserCircle className="h-5 w-5 text-muted-foreground" />
              حساب کاربری
            </CardTitle>
            <CardDescription className="text-muted-foreground/80 mt-2">
              مدیریت اطلاعات شخصی، تغییر ایمیل و تنظیمات امنیتی رمز عبور.
            </CardDescription>
          </CardHeader>
          <CardContent className="pt-4">
            <Button asChild variant="outline" className="w-full bg-transparent border-border/50 hover:bg-muted/50">
              <Link href="/dashboard/profile">تنظیمات حساب</Link>
            </Button>
          </CardContent>
        </Card>

        {user?.role === "admin" && (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg text-foreground">
                <Users className="h-5 w-5 text-muted-foreground" />
                مدیریت دسترسی‌ها
              </CardTitle>
              <CardDescription className="text-muted-foreground/80 mt-2">
                افزودن همکاران جدید، ویرایش نقش‌ها و مدیریت کاربران سیستم.
              </CardDescription>
            </CardHeader>
            <CardContent className="pt-4">
              <Button asChild variant="outline" className="w-full bg-transparent border-border/50 hover:bg-muted/50">
                <Link href="/dashboard/users">رفتن به بخش کاربران</Link>
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}