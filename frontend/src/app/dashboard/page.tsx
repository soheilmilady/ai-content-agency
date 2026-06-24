import Link from "next/link";
import { FilePlus2, UserCircle, Users } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export default function DashboardPage() {
  return (
    <div dir="rtl" className="mx-auto max-w-4xl space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground">داشبورد</h2>
        <p className="mt-1 text-muted-foreground">
          به پلتفرم محتوای هوشمند خوش آمدید. از اینجا کارهای اصلی را شروع کنید.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {/* جایگزینی glass-panel با bg-card و border-border */}
        <Card className="border border-border bg-card text-card-foreground shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg text-foreground">
              <FilePlus2 className="h-5 w-5 text-primary" />
              تولید مقاله
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              مقاله سئو محور جدید با هوش مصنوعی بسازید.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="bg-primary text-primary-foreground hover:bg-primary/90">
              <Link href="/dashboard/articles/new">شروع تولید محتوا</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="border border-border bg-card text-card-foreground shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg text-foreground">
              <UserCircle className="h-5 w-5 text-primary" />
              حساب کاربری
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              تغییر ایمیل، نام کاربری و رمز عبور.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link href="/dashboard/profile">مدیریت حساب</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="border border-border bg-card text-card-foreground shadow-sm transition-all hover:shadow-md">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg text-foreground">
              <Users className="h-5 w-5 text-primary" />
              مدیریت کاربران
            </CardTitle>
            <CardDescription className="text-muted-foreground">
              افزودن، ویرایش و حذف کاربران (فقط admin).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link href="/dashboard/users">رفتن به مدیریت کاربران</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}