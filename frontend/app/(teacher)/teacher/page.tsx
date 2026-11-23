import type { Metadata } from "next";
import { ArrowRight, ClipboardCheck, Users } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { ProjectStatusBadge } from "@/components/project-status-badge";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { className } from "@/lib/format";
import { serverApiGet } from "@/lib/server-api";
import type { Submission, TeacherStudent } from "@/types/api";

export const metadata: Metadata = { title: "Мои ученики" };

export default function TeacherPage() {
  return (
    <div className="space-y-8">
      <header className="glass-sky relative overflow-hidden rounded-[var(--r-2xl)] p-6 sm:p-8">
        <div
          aria-hidden="true"
          className="absolute -right-12 -top-16 size-48 rounded-full bg-sky-gradient opacity-25 blur-3xl"
        />
        <div className="relative space-y-3">
          <Badge variant="secondary">Кабинет учителя</Badge>
          <h1 className="text-3xl leading-tight sm:text-4xl">
            Мои <span className="text-gradient">ученики</span>
          </h1>
          <p className="max-w-[70ch] text-[var(--muted-foreground)]">
            Дети из всех ваших классов. В карточке видно, в каком классе учится
            ученик и на каком этапе его проект.
          </p>
        </div>
      </header>

      <Suspense fallback={<Skeleton className="h-32 w-full" />}>
        <ReviewQueueCard />
      </Suspense>

      <Suspense fallback={<StudentsSkeleton />}>
        <TeacherStudents />
      </Suspense>
    </div>
  );
}

async function ReviewQueueCard() {
  await requireUser();
  const queue = await serverApiGet<Submission[]>("/teacher/submissions?status=submitted");

  if (queue === null) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-lg">
            <ClipboardCheck className="size-5 text-[var(--primary)]" aria-hidden="true" />
            Темы на проверке
          </CardTitle>
          <Badge variant={queue.length > 0 ? "warning" : "success"}>
            {queue.length > 0 ? `${queue.length} ждут решения` : "Очередь пуста"}
          </Badge>
        </div>
        <CardDescription>
          Каждая заявка уже проверена на повтор и ширину — остаётся решение и комментарий.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-2">
        <Link href="/teacher/submissions" className={buttonVariants({ size: "sm" })}>
          Проверить темы
          <ArrowRight aria-hidden="true" />
        </Link>
        <Link
          href="/teacher/topics"
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          Реестр тем
        </Link>
        <Link
          href="/teacher/projects"
          className={buttonVariants({ variant: "outline", size: "sm" })}
        >
          Проекты учеников
        </Link>
      </CardContent>
    </Card>
  );
}

async function TeacherStudents() {
  await requireUser();
  const students = await serverApiGet<TeacherStudent[]>("/teacher/students");

  if (students === null) {
    return <Alert>Не удалось загрузить учеников. Обновите страницу или войдите заново.</Alert>;
  }

  if (students.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Пока нет учеников</CardTitle>
          <CardDescription>
            Администратор школы назначит вас куратором класса — и ученики появятся здесь.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {students.map((student) => (
        <Card key={student.user_id}>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-lg">{student.full_name}</CardTitle>
                <CardDescription className="flex flex-wrap items-center gap-2">
                  <Users className="size-4" aria-hidden="true" />
                  <span className="font-medium text-[var(--foreground)]">
                    {className({ grade: student.class_grade, label: student.class_label })}
                  </span>
                  <span aria-hidden="true">·</span>
                  {student.academic_year_name ?? "Текущий год"}
                </CardDescription>
              </div>
              {student.project_status ? (
                <ProjectStatusBadge status={student.project_status} />
              ) : (
                <Badge variant="secondary">Проект не начат</Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-[var(--muted-foreground)]">{student.email}</p>
            <div className="flex flex-wrap gap-2">
              {student.project_id ? (
                <Link
                  href={`/teacher/projects/${student.project_id}`}
                  className={buttonVariants({ size: "sm" })}
                >
                  Открыть проект
                  <ArrowRight aria-hidden="true" />
                </Link>
              ) : null}
              <Link
                href={`/teacher/classes/${student.class_id}`}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                Дашборд класса
              </Link>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function StudentsSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-56 w-full" />
    </div>
  );
}
