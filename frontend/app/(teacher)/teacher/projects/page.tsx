import type { Metadata } from "next";
import { ArrowRight, FolderKanban, MessageSquare, Paperclip, Users } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { ProjectStatusBadge } from "@/components/project-status-badge";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { serverApiGet } from "@/lib/server-api";
import type { TeacherProject } from "@/types/api";

export const metadata: Metadata = { title: "Проекты учеников" };

export default function TeacherProjectsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Проекты учеников</h1>
          <Link
            href="/teacher/submissions"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Проверка тем
          </Link>
        </div>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Карточки проектов ваших классов: продукт, чек-лист, файлы и комментарии.
        </p>
      </header>

      <Suspense fallback={<ProjectsSkeleton />}>
        <ProjectsContent />
      </Suspense>
    </div>
  );
}

async function ProjectsContent() {
  await requireUser();
  const projects = await serverApiGet<TeacherProject[]>("/teacher/projects");

  if (projects === null) {
    return <Alert>Не удалось загрузить проекты. Обновите страницу или войдите заново.</Alert>;
  }

  if (projects.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <FolderKanban className="size-5 text-[var(--primary)]" aria-hidden="true" />
            Пока нет проектов
          </CardTitle>
          <CardDescription>
            Проекты появятся здесь, когда ученики ваших классов начнут работу.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link href="/teacher" className={buttonVariants({ variant: "outline" })}>
            Вернуться к ученикам
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {projects.map((project) => (
        <Card key={project.id}>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="text-lg">{project.student_full_name}</CardTitle>
                <CardDescription className="flex flex-wrap items-center gap-2">
                  <Users className="size-3.5" aria-hidden="true" />
                  {project.class_grade}
                  {project.class_label} · {project.academic_year_name ?? "текущий год"}
                </CardDescription>
              </div>
              <ProjectStatusBadge status={project.status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1 text-sm">
              <p className="font-medium">
                {project.topic_title ?? "Тема ещё не сформулирована"}
              </p>
              {project.research_question ? (
                <p className="text-[var(--muted-foreground)]">{project.research_question}</p>
              ) : null}
              {project.product_category_name ? (
                <p className="text-[var(--muted-foreground)]">
                  Продукт: {project.product_category_name}
                </p>
              ) : null}
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">
                <Paperclip className="mr-1 size-3" aria-hidden="true" />
                {project.files_count} файлов
              </Badge>
              <Badge variant="secondary">
                <MessageSquare className="mr-1 size-3" aria-hidden="true" />
                {project.comments_count} комментариев
              </Badge>
              <span className="text-xs text-[var(--muted-foreground)]">
                Активность: {formatDateTime(project.last_activity_at)}
              </span>
            </div>

            <Link
              href={`/teacher/projects/${project.id}`}
              className={buttonVariants({ size: "sm" })}
            >
              Открыть проект
              <ArrowRight aria-hidden="true" />
            </Link>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ProjectsSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-3">
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-48 w-full" />
      <Skeleton className="h-48 w-full" />
    </div>
  );
}
