"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import {
  LayoutDashboard,
  LogOut,
  UserCircle,
  Users,
  Sparkles,
  Menu,
  FileText
} from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { getMe, type User } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "داشبورد", icon: LayoutDashboard },
  { href: "/dashboard/articles/new", label: "تولید هوشمند", icon: Sparkles },
  { href: "/dashboard/articles", label: "لیست مقالات", icon: FileText },
  { href: "/dashboard/profile", label: "حساب کاربری", icon: UserCircle },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);

  useEffect(() => {
    const token = Cookies.get("auth_token");
    if (!token) {
      router.replace("/login");
      return;
    }

    getMe()
      .then(setUser)
      .catch(() => {
        Cookies.remove("auth_token");
        router.replace("/login");
      })
      .finally(() => setLoading(false));
  }, [router]);

  function handleLogout() {
    Cookies.remove("auth_token");
    router.replace("/login");
  }

  if (loading) {
    return (
      <div dir="rtl" className="flex min-h-screen bg-background text-foreground">
        <aside className="fixed inset-y-0 right-0 hidden w-64 flex-col border-l border-border/50 bg-muted/10 animate-pulse md:flex">
          <div className="border-b border-border/50 h-[89px]"></div>
          <div className="p-4 space-y-3">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-10 w-full bg-muted/40 rounded-xl"></div>
            ))}
          </div>
        </aside>
        <div className="md:mr-64 flex min-h-screen flex-1 flex-col relative w-full">
          <header className="sticky top-0 h-[73px] border-b border-border/50 bg-muted/10 animate-pulse"></header>
          <main className="flex-1 p-8">
            <div className="max-w-5xl mx-auto space-y-8">
              <div className="h-10 w-64 bg-muted/40 rounded-lg animate-pulse"></div>
              <div className="h-[400px] w-full bg-muted/20 rounded-2xl animate-pulse"></div>
            </div>
          </main>
        </div>
      </div>
    );
  }

  const sidebarItems = [
    ...navItems,
    ...(user?.role === "admin"
      ? [{ href: "/dashboard/users", label: "مدیریت کاربران", icon: Users }]
      : []),
  ];

  return (
    <div dir="rtl" className="flex min-h-screen bg-background bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-primary/5 via-background to-background text-foreground transition-colors duration-300">
      
      {/* سایدبار شیشه‌ای */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 z-20 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
      <aside className={`fixed inset-y-0 right-0 z-30 flex w-64 flex-col border-l border-border/50 bg-background/90 md:bg-background/60 backdrop-blur-xl shadow-sm transform transition-transform duration-300 ease-in-out md:translate-x-0 ${isSidebarOpen ? "translate-x-0" : "translate-x-full"}`}>
        <div className="border-b border-border/50 px-6 py-6 flex items-center gap-3">
          <div className="bg-primary/10 p-2 rounded-lg text-primary">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-base font-extrabold tracking-tight">AI content generator</h1>
            <p className="text-xs text-muted-foreground font-medium">پنل مدیریت محتوا</p>
          </div>
        </div>

        <nav className="flex-1 space-y-1.5 p-4">
          {sidebarItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-semibold transition-all duration-200 ${
                  active
                    ? "bg-primary text-primary-foreground shadow-md shadow-primary/20 scale-[1.02]"
                    : "text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                }`}
                onClick={() => setIsSidebarOpen(false)}
              >
                <Icon className={`h-4 w-4 ${active ? "opacity-100" : "opacity-70"}`} />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="md:mr-64 flex min-h-screen flex-1 flex-col relative w-full">
        {/* هدر شیشه‌ای و مدرن */}
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-border/50 bg-background/60 backdrop-blur-xl px-4 md:px-8 py-4 shadow-sm">
          <div className="flex items-center gap-3">
            <Button 
              variant="ghost" 
              size="icon" 
              className="md:hidden" 
              onClick={() => setIsSidebarOpen(true)}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="flex flex-col hidden sm:flex">
              <p className="text-xs font-medium text-muted-foreground mb-0.5">خوش آمدید</p>
              <p className="text-sm font-bold text-foreground">{user?.username || user?.email}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button variant="ghost" size="sm" onClick={handleLogout} className="text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors">
              <LogOut className="ml-2 h-4 w-4" />
              خروج
            </Button>
          </div>
        </header>

        <main className="flex-1 p-8">{children}</main>
      </div>
    </div>
  );
}