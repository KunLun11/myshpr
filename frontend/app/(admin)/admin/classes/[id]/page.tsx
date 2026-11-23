import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { InvitePanel } from "@/components/invite-panel";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { className } from "@/lib/format";
import { serverApiGet } from "@/lib/server-api";
import type { ClassSummary, StudentSummary } from "@/types/api";

export const metadata: Metadata = { title: "Класс" };
export const instant = false;

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function AdminClassPage({ params }: PageProps) {
  return (
    <Suspense fallback={<ClassSkeleton />}>
      <ClassDetail params={params} />
    </Suspense>
  );
}

async function ClassDetail({ params }: PageProps) {
  const { id } = await params;
  const [schoolClass, students] = await Promise.all([
    serverApiGet<ClassSummary>(`/admin/classes/${id}`),
    serverApiGet<StudentSummary[]>(`/admin/classes/${id}/students`),
  ]);

  if (schoolClass === null) {
    return (
      <div className="space-y-4">
        <Alert>Класс не найден или нет доступа.</Alert>
        <Link href="/admin" className="text-sm font-medium text-[var(--primary)]">
          Вернуться к классам
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <Link href="/admin" className="text-sm text-[var(--muted-foreground)]">
          ← Все классы
        </Link>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">{className(schoolClass)}</h1>
          <Badge variant="secondary">{schoolClass.academic_year_name ?? "Текущий год"}</Badge>
        </div>
        <p className="text-[var(--muted-foreground)]">
          {schoolClass.students_count} учеников в классе
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>Приглашение в класс</CardTitle>
          <CardDescription>
            Отправьте ученику код или ссылку. Код действует 14 дней.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <InvitePanel classId={schoolClass.id} />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ученики</CardTitle>
          <CardDescription>Список зарегистрированных учеников класса.</CardDescription>
        </CardHeader>
        <CardContent>
          {students === null ? (
            <Alert variant="info">Не удалось загрузить список учеников.</Alert>
          ) : students.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">
              Пока никто не зарегистрировался по коду класса.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-[var(--muted-foreground)]">
                  <tr>
                    <th className="py-2 pr-4 font-medium">ФИО</th>
                    <th className="py-2 font-medium">Email</th>
                  </tr>
                </thead>
                <tbody>
                  {students.map((student) => (
                    <tr key={student.user_id} className="border-t border-[var(--border)]">
                      <td className="py-3 pr-4">{student.full_name}</td>
                      <td className="py-3 text-[var(--muted-foreground)]">{student.email}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ClassSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-8">
      <div className="space-y-3">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-40" />
      </div>
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
