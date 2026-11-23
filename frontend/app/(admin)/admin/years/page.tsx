import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { AdminYears } from "@/components/admin/admin-years";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { AcademicYear, School } from "@/types/api";

export const metadata: Metadata = { title: "Учебные годы" };
export const instant = false;

export default function AdminYearsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Учебные годы</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Текущий год задаёт классы, шаблон чек-листа и контрольные точки. У школы может быть
          только один текущий год.
        </p>
      </header>
      <Suspense fallback={<YearsSkeleton />}>
        <YearsSection />
      </Suspense>
    </div>
  );
}

async function YearsSection() {
  const user = await requireUser();
  const [years, schools] = await Promise.all([
    serverApiGet<AcademicYear[]>("/admin/academic-years"),
    serverApiGet<School[]>("/admin/schools"),
  ]);

  if (years === null || schools === null) {
    return <Alert>Не удалось загрузить учебные годы. Обновите страницу.</Alert>;
  }
  if (schools.length === 0) {
    return (
      <Alert variant="info">
        Сначала создайте школу в разделе{" "}
        <Link href="/admin/schools" className="font-medium underline-offset-4 hover:underline">
          «Школы»
        </Link>
        .
      </Alert>
    );
  }

  return (
    <AdminYears
      years={years}
      schools={schools}
      canPickSchool={user.role === "super_admin"}
    />
  );
}

function YearsSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-80 w-full" />
    </div>
  );
}
