"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Trash2 } from "lucide-react";

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
import {
  createUser,
  deleteUser,
  getMe,
  getUsers,
  updateUser,
  type User,
} from "@/lib/api";

const ROLES = [
  { value: "admin", label: "مدیر" },
  { value: "editor", label: "ویرایشگر" },
  { value: "writer", label: "نویسنده" },
  { value: "viewer", label: "بیننده" },
];

export default function UsersPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("writer");
  const [submitting, setSubmitting] = useState(false);

  async function loadUsers() {
    const data = await getUsers();
    setUsers(data);
  }

  useEffect(() => {
    getMe()
      .then((me) => {
        if (me.role !== "admin") {
          router.replace("/dashboard");
          return;
        }
        return loadUsers();
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      await createUser({ email, username, password, role });
      setEmail("");
      setUsername("");
      setPassword("");
      setRole("writer");
      setMessage("کاربر جدید با موفقیت ایجاد شد.");
      await loadUsers();
    } catch {
      setError("ایجاد کاربر با خطا مواجه شد.");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleRoleChange(userId: number, newRole: string) {
    setError("");
    try {
      await updateUser(userId, { role: newRole });
      await loadUsers();
    } catch {
      setError("به‌روزرسانی نقش کاربر با خطا مواجه شد.");
    }
  }

  async function handleToggleActive(user: User) {
    setError("");
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      await loadUsers();
    } catch {
      setError("به‌روزرسانی وضعیت کاربر با خطا مواجه شد.");
    }
  }

  async function handleDelete(user: User) {
    if (!confirm(`آیا از حذف کاربر «${user.username}» مطمئن هستید؟`)) return;

    setError("");
    try {
      await deleteUser(user.id);
      setMessage("کاربر حذف شد.");
      await loadUsers();
    } catch {
      setError("حذف کاربر با خطا مواجه شد.");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-muted-foreground">
        <Loader2 className="ml-2 h-5 w-5 animate-spin" />
        در حال بارگذاری...
      </div>
    );
  }

  return (
    <div dir="rtl" className="mx-auto max-w-5xl space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-foreground">مدیریت کاربران</h2>
        <p className="mt-1 text-muted-foreground">
          کاربران سیستم را مشاهده، اضافه و مدیریت کنید.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>افزودن کاربر جدید</CardTitle>
          <CardDescription>فقط مدیران می‌توانند کاربر جدید بسازند.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleCreate} className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="email">ایمیل</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                dir="ltr"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="username">نام کاربری</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">رمز عبور</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                dir="ltr"
              />
            </div>
            <div className="space-y-2">
              <Label>نقش</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="md:col-span-2">
              <Button
                type="submit"
                disabled={submitting}
                className="bg-indigo-600 hover:bg-indigo-500"
              >
                {submitting ? (
                  <>
                    <Loader2 className="ml-2 h-4 w-4 animate-spin" />
                    در حال ایجاد...
                  </>
                ) : (
                  "ایجاد کاربر"
                )}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {error && (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/60 dark:text-red-300">
          {error}
        </p>
      )}
      {message && (
        <p className="rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800 dark:border-green-900 dark:bg-green-950/60 dark:text-green-300">
          {message}
        </p>
      )}

      <Card>
        <CardHeader>
          <CardTitle>لیست کاربران</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-right text-muted-foreground">
                  <th className="px-3 py-2 font-medium">نام کاربری</th>
                  <th className="px-3 py-2 font-medium">ایمیل</th>
                  <th className="px-3 py-2 font-medium">نقش</th>
                  <th className="px-3 py-2 font-medium">وضعیت</th>
                  <th className="px-3 py-2 font-medium">عملیات</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => (
                  <tr key={user.id} className="border-b border-border">
                    <td className="px-3 py-3 font-medium text-foreground">
                      {user.username}
                    </td>
                    <td className="px-3 py-3 text-muted-foreground" dir="ltr">
                      {user.email}
                    </td>
                    <td className="px-3 py-3">
                      <Select
                        value={user.role}
                        onValueChange={(value) =>
                          handleRoleChange(user.id, value)
                        }
                      >
                        <SelectTrigger className="h-8 w-36">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {ROLES.map((r) => (
                            <SelectItem key={r.value} value={r.value}>
                              {r.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-3 py-3">
                      <Badge
                        className={
                          user.is_active
                            ? "bg-green-100 text-green-800 hover:bg-green-100 dark:bg-green-950 dark:text-green-300"
                            : "bg-red-100 text-red-800 hover:bg-red-100 dark:bg-red-950 dark:text-red-300"
                        }
                      >
                        {user.is_active ? "فعال" : "غیرفعال"}
                      </Badge>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleToggleActive(user)}
                        >
                          {user.is_active ? "غیرفعال" : "فعال"}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDelete(user)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
