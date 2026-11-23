import type { Metadata } from "next";
import { Suspense } from "react";

import { AdminStudents } from "@/components/admin/admin-students";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { AdminStudent, ClassSummary } from "@/types/api";

export const metadata: Metadata = { title: "Ученики" };
export const instant = false;

export default function AdminStudentsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Ученики</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Список учеников школы и импорт из CSV. Обычная регистрация — по коду приглашения класса.
        </p>
      </header>
      <Suspense fallback={<StudentsSkeleton />}>
        <StudentsSection />
      </Suspense>
    </div>
  );
}

async function StudentsSection() {
  await requireUser();
  const [students, classes] = await Promise.all([
    serverApiGet<AdminStudent[]>("/admin/students"),
    serverApiGet<ClassSummary[]>("/admin/classes"),
  ]);

  if (students === null || classes === null) {
    return <Alert>Не удалось загрузить учеников. Обновите страницу.</Alert>;
  }

  return <AdminStudents students={students} classes={classes} />;
}

function StudentsSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <Skeleton className="h-72 w-full" />
      <Skeleton className="h-96 w-full" />
    </div>
  );
}
