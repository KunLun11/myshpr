import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Users } from "lucide-react";
import { Suspense } from "react";

import { CreateClassForm } from "@/components/create-class-form";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { className } from "@/lib/format";
import { serverApiGet } from "@/lib/server-api";
import type { ClassSummary, School } from "@/types/api";

export const metadata: Metadata = { title: "Классы школы" };

export default async function AdminPage() {
  const user = await requireUser();
  const canPickSchool = user.role === "super_admin";
  const schools = canPickSchool ? await serverApiGet<School[]>("/admin/schools") : null;

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Классы школы</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Управление классами и кодами приглашения. Справочники, чек-листы, контрольные точки
          и аудит — в разделах ниже.
        </p>
      </header>

      <AdminShortcuts />

      <CreateClassForm schools={schools ?? []} canPickSchool={canPickSchool} />

      <Suspense fallback={<ClassesSkeleton />}>
        <AdminClasses />
      </Suspense>
    </div>
  );
}

async function AdminClasses() {
  await requireUser();
  const classes = await serverApiGet<ClassSummary[]>("/admin/classes");

  if (classes === null) {
    return <Alert>Не удалось загрузить классы. Обновите страницу или войдите заново.</Alert>;
  }

  if (classes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Классов пока нет</CardTitle>
          <CardDescription>Создайте первый класс — например, 9А.</CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {classes.map((item) => (
        <Card key={item.id}>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>{className(item)}</CardTitle>
              <Badge variant="secondary">{item.academic_year_name ?? "Текущий год"}</Badge>
            </div>
            <CardDescription className="flex items-center gap-2">
              <Users className="size-4" aria-hidden="true" />
              {item.students_count} учеников
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              href={`/admin/classes/${item.id}`}
              className={buttonVariants({ variant: "outline", size: "sm" })}
            >
              Открыть класс
              <ArrowRight aria-hidden="true" />
            </Link>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ClassesSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <Skeleton className="h-52 w-full" />
      <Skeleton className="h-52 w-full" />
      <Skeleton className="h-52 w-full" />
    </div>
  );
}

const SHORTCUTS = [
  { href: "/admin/years", label: "Учебные годы" },
  { href: "/admin/references", label: "Справочники" },
  { href: "/admin/checklist", label: "Чек-лист" },
  { href: "/admin/checkpoints", label: "Контрольные точки" },
  { href: "/admin/students", label: "Ученики и импорт" },
  { href: "/admin/audit", label: "Журнал действий" },
];

function AdminShortcuts() {
  return (
    <nav aria-label="Разделы админки" className="flex flex-wrap gap-2">
      {SHORTCUTS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
