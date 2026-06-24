"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import {
  FilePlus2,
  LayoutDashboard,
  LogOut,
  UserCircle,
  Users,
} from "lucide-react";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { getMe, type User } from "@/lib/api";

const navItems = [
  { href: "/dashboard", label: "داشبورد", icon: LayoutDashboard },
  { href: "/dashboard/articles/new", label: "مقالات جدید", icon: FilePlus2 },
  { href: "/dashboard/profile", label: "حساب کاربری", icon: UserCircle },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

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
      <div
        dir="rtl"
        className="flex min-h-screen items-center justify-center bg-background"
      >
        <p className="text-muted-foreground">در حال بارگذاری...</p>
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
    <div dir="rtl" className="flex min-h-screen bg-background text-foreground">
      <aside className="glass-panel fixed inset-y-0 right-0 z-30 flex w-64 flex-col">
        <div className="border-b border-border px-6 py-5">
          <h1 className="text-lg font-bold">پلتفرم محتوای هوشمند</h1>
          <p className="mt-1 text-xs text-muted-foreground">پنل مدیریت</p>
        </div>

        <nav className="flex-1 space-y-1 p-4">
          {sidebarItems.map(({ href, label, icon: Icon }) => {
            const active =
              pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="mr-64 flex min-h-screen flex-1 flex-col">
        <header className="glass-panel sticky top-0 z-20 flex items-center justify-between px-6 py-4">
          <div>
            <p className="text-sm text-muted-foreground">خوش آمدید</p>
            <p className="font-semibold">{user?.username || user?.email}</p>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="outline" size="sm" onClick={handleLogout}>
              <LogOut className="ml-2 h-4 w-4" />
              خروج
            </Button>
          </div>
        </header>

        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
