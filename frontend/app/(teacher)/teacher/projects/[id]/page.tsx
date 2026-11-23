import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { ProjectStatusBadge } from "@/components/project-status-badge";
import { TeacherProjectWorkspace } from "@/components/teacher-project-workspace";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type {
  ProjectChecklist,
  ProjectFile,
  TeacherComment,
  TeacherProject,
} from "@/types/api";

export const metadata: Metadata = { title: "Карточка проекта" };
export const instant = false;

interface PageProps {
  params: Promise<{ id: string }>;
}

export default function TeacherProjectPage({ params }: PageProps) {
  return (
    <Suspense fallback={<ProjectSkeleton />}>
      <ProjectContent params={params} />
    </Suspense>
  );
}

async function ProjectContent({ params }: PageProps) {
  const { id } = await params;
  await requireUser();

  const project = await serverApiGet<TeacherProject>(`/teacher/projects/${id}`);
  if (project === null) {
    return (
      <div className="space-y-4">
        <Alert>Проект не найден или нет доступа.</Alert>
        <Link href="/teacher/projects" className="text-sm font-medium text-[var(--primary)]">
          Вернуться к проектам
        </Link>
      </div>
    );
  }

  const [checklist, files, comments] = await Promise.all([
    serverApiGet<ProjectChecklist>(`/teacher/projects/${id}/checklist`),
    serverApiGet<ProjectFile[]>(`/teacher/projects/${id}/files`),
    serverApiGet<TeacherComment[]>(`/teacher/projects/${id}/comments`),
  ]);

  if (!checklist) {
    return <Alert>Не удалось загрузить чек-лист проекта. Обновите страницу.</Alert>;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <Link href="/teacher/projects" className="text-sm text-[var(--muted-foreground)]">
          ← Все проекты
        </Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="space-y-1">
            <h1 className="text-3xl font-semibold tracking-tight">
              {project.student_full_name}
            </h1>
            <p className="text-sm text-[var(--muted-foreground)]">
              {project.class_grade}
              {project.class_label} · {project.academic_year_name ?? "текущий год"}
            </p>
          </div>
          <ProjectStatusBadge status={project.status} />
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge variant="secondary">{project.files_count} файлов</Badge>
          <Badge variant="secondary">{project.comments_count} комментариев</Badge>
        </div>
      </header>

      <TeacherProjectWorkspace
        project={project}
        checklist={checklist}
        files={files ?? []}
        comments={comments ?? []}
      />
    </div>
  );
}

function ProjectSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-9 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
      <Skeleton className="h-12 w-full rounded-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
