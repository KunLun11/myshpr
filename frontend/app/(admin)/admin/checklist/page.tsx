import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AdminChecklist } from "@/components/admin/admin-checklist";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { AcademicYear, AdminChecklistItem } from "@/types/api";

export const metadata: Metadata = { title: "Шаблон чек-листа" };
export const instant = false;

export default function AdminChecklistPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Шаблон чек-листа</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Пункты по этапам проекта. Обязательные пункты влияют на прогресс и напоминания.
        </p>
      </header>
      <Suspense fallback={<ChecklistSkeleton />}>
        <ChecklistSection />
      </Suspense>
    </div>
  );
}

async function ChecklistSection() {
  await requireUser();
  const [items, years] = await Promise.all([
    serverApiGet<AdminChecklistItem[]>("/admin/checklist-items"),
    serverApiGet<AcademicYear[]>("/admin/academic-years"),
  ]);

  if (items === null || years === null) {
    return <Alert>Не удалось загрузить шаблон чек-листа. Обновите страницу.</Alert>;
  }
  if (years.length === 0) {
    return (
      <Alert variant="info">
        Сначала создайте учебный год в разделе{" "}
        <Link href="/admin/years" className="font-medium underline-offset-4 hover:underline">
          «Годы»
        </Link>
        .
      </Alert>
    );
  }

  return <AdminChecklist items={items} years={years} />;
}

function ChecklistSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-96 w-full" />
    </div>
  );
}
