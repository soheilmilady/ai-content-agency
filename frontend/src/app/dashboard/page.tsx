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
        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FilePlus2 className="h-5 w-5 text-indigo-600" />
              تولید مقاله
            </CardTitle>
            <CardDescription>
              مقاله سئو محور جدید با هوش مصنوعی بسازید.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="bg-indigo-600 hover:bg-indigo-500">
              <Link href="/dashboard/articles/new">شروع تولید محتوا</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <UserCircle className="h-5 w-5 text-indigo-600" />
              حساب کاربری
            </CardTitle>
            <CardDescription>
              تغییر ایمیل، نام کاربری و رمز عبور.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline">
              <Link href="/dashboard/profile">مدیریت حساب</Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="glass-panel">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Users className="h-5 w-5 text-indigo-600" />
              مدیریت کاربران
            </CardTitle>
            <CardDescription>
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
