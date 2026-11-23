import type { Metadata } from "next";
import { Suspense } from "react";

import { AdminSchools } from "@/components/admin/admin-schools";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireRole } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { School } from "@/types/api";

export const metadata: Metadata = { title: "Школы" };
export const instant = false;

export default function AdminSchoolsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Школы</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Платформенные школы, их города и часовые пояса. Доступно только суперадмину.
        </p>
      </header>
      <Suspense fallback={<PanelSkeleton />}>
        <SchoolsSection />
      </Suspense>
    </div>
  );
}

async function SchoolsSection() {
  await requireRole("super_admin");
  const schools = await serverApiGet<School[]>("/admin/schools");
  if (schools === null) {
    return <Alert>Не удалось загрузить школы. Обновите страницу или войдите заново.</Alert>;
  }
  return <AdminSchools schools={schools} />;
}

function PanelSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-80 w-full" />
    </div>
  );
}
