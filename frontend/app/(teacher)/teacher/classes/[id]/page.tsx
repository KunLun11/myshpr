import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { StuckDashboard } from "@/components/stuck-dashboard";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { ClassDashboard } from "@/types/api";

export const metadata: Metadata = { title: "Дашборд класса" };
export const instant = false;

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function ClassDashboardPage({ params }: PageProps) {
  return (
    <Suspense fallback={<DashboardSkeleton />}>
      <DashboardContent params={params} />
    </Suspense>
  );
}

async function DashboardContent({ params }: PageProps) {
  const { id } = await params;
  await requireUser();
  const dashboard = await serverApiGet<ClassDashboard>(
    `/teacher/classes/${id}/dashboard`,
  );

  if (dashboard === null) {
    return (
      <div className="space-y-4">
        <Alert>Класс не найден или нет доступа. Возможно, вы не куратор этого класса.</Alert>
        <Link href="/teacher" className="text-sm font-medium text-[var(--primary)]">
          Вернуться к классам
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link href="/teacher" className="text-sm text-[var(--muted-foreground)]">
          ← Мои ученики
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <h1 className="text-3xl font-semibold tracking-tight">
              Кто застрял: {dashboard.class_grade}
              {dashboard.class_label}
            </h1>
            <p className="max-w-[70ch] text-[var(--muted-foreground)]">
              Цвет всегда объяснён причиной: активность, контрольные точки, чек-лист и
              итоговый файл. Сначала показаны те, кому нужнее помощь.
            </p>
          </div>
          <Badge variant="secondary">
            {dashboard.academic_year_name ?? "Текущий учебный год"}
          </Badge>
        </div>
      </header>

      <StuckDashboard classId={id} initial={dashboard} />
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <Skeleton className="h-10 w-2/3" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-28 w-full" />
      </div>
      <Skeleton className="h-11 w-full" />
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-56 w-full" />
    </div>
  );
}
