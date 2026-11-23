import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AdminCheckpoints } from "@/components/admin/admin-checkpoints";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { AcademicYear, AdminCheckpoint } from "@/types/api";

export const metadata: Metadata = { title: "Контрольные точки" };
export const instant = false;

export default function AdminCheckpointsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Контрольные точки</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Сроки, по которым учитель видит отставание, а ученик — следующий шаг в кабинете.
        </p>
      </header>
      <Suspense fallback={<CheckpointsSkeleton />}>
        <CheckpointsSection />
      </Suspense>
    </div>
  );
}

async function CheckpointsSection() {
  await requireUser();
  const [checkpoints, years] = await Promise.all([
    serverApiGet<AdminCheckpoint[]>("/admin/checkpoints"),
    serverApiGet<AcademicYear[]>("/admin/academic-years"),
  ]);

  if (checkpoints === null || years === null) {
    return <Alert>Не удалось загрузить контрольные точки. Обновите страницу.</Alert>;
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

  return <AdminCheckpoints checkpoints={checkpoints} years={years} />;
}

function CheckpointsSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <Skeleton className="h-72 w-full" />
      <Skeleton className="h-96 w-full" />
    </div>
  );
}
