import type { Metadata } from "next";
import { ArrowRight, ClipboardCheck, Users } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { InvitePanel } from "@/components/invite-panel";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { className } from "@/lib/format";
import { serverApiGet } from "@/lib/server-api";
import type { ClassSummary, Submission } from "@/types/api";

export const metadata: Metadata = { title: "Мои классы" };

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
            Мои <span className="text-gradient">классы</span>
          </h1>
          <p className="max-w-[70ch] text-[var(--muted-foreground)]">
            Классы, где вы куратор. Код приглашения даёт ученику возможность
            зарегистрироваться и попасть в класс.
          </p>
        </div>
      </header>

      <Suspense fallback={<Skeleton className="h-32 w-full" />}>
        <ReviewQueueCard />
      </Suspense>

      <Suspense fallback={<ClassesSkeleton />}>
        <TeacherClasses />
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

async function TeacherClasses() {
  await requireUser();
  const classes = await serverApiGet<ClassSummary[]>("/teacher/classes");

  if (classes === null) {
    return <Alert>Не удалось загрузить классы. Обновите страницу или войдите заново.</Alert>;
  }

  if (classes.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Пока нет классов</CardTitle>
          <CardDescription>
            Администратор школы назначит вас куратором — и классы появятся здесь.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {classes.map((item) => (
        <Card key={item.id} interactive>
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
          <CardContent className="space-y-4">
            <Link
              href={`/teacher/classes/${item.id}`}
              className={buttonVariants({ size: "sm" })}
            >
              Дашборд класса
              <ArrowRight aria-hidden="true" />
            </Link>
            <InvitePanel classId={item.id} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ClassesSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="grid gap-4 sm:grid-cols-2">
      <Skeleton className="h-56 w-full" />
      <Skeleton className="h-56 w-full" />
    </div>
  );
}
