import type { Metadata } from "next";
import { ArrowRight, FolderOpen } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { ProjectStatusBadge } from "@/components/project-status-badge";
import { WorkTabs } from "@/components/work-tabs";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type {
  Project,
  ProjectChecklist,
  ProjectFile,
  TeacherComment,
} from "@/types/api";

export const metadata: Metadata = { title: "Работа над проектом" };

export default function WorkPage() {
  return (
    <Suspense fallback={<WorkSkeleton />}>
      <WorkContent />
    </Suspense>
  );
}

async function WorkContent() {
  await requireUser();
  const project = await serverApiGet<Project | null>("/me/project");

  if (!project) {
    return (
      <div className="space-y-6">
        <header className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">Работа над проектом</h1>
          <p className="max-w-[70ch] text-[var(--muted-foreground)]">
            Чек-лист, файлы и комментарии появятся после того, как начнётся работа
            над проектом.
          </p>
        </header>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <FolderOpen className="size-5 text-[var(--primary)]" aria-hidden="true" />
              Сначала сформулируйте тему
            </CardTitle>
            <CardDescription>
              Мастер темы поможет выбрать сферу, вопрос и формулировку. После этого
              откроется работа над проектом.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/cabinet/topic" className={buttonVariants()}>
              Открыть мастер темы
              <ArrowRight aria-hidden="true" />
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const [checklist, files, comments] = await Promise.all([
    serverApiGet<ProjectChecklist>("/me/project/checklist"),
    serverApiGet<ProjectFile[]>("/me/project/files"),
    serverApiGet<TeacherComment[]>("/me/project/comments"),
  ]);

  if (!checklist) {
    return <Alert>Не удалось загрузить чек-лист. Обновите страницу или войдите заново.</Alert>;
  }

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Работа над проектом</h1>
          <ProjectStatusBadge status={project.status} />
        </div>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Отмечайте пункты чек-листа, загружайте файлы и читайте комментарии учителя.
          Всё сохраняется сразу — перезагружать страницу не нужно.
        </p>
        {project.topic?.title ? (
          <p className="text-sm text-[var(--muted-foreground)]">
            Тема: «{project.topic.title}»
          </p>
        ) : null}
      </header>

      <WorkTabs checklist={checklist} files={files ?? []} comments={comments ?? []} />
    </div>
  );
}

function WorkSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-9 w-80" />
        <Skeleton className="h-4 w-full max-w-xl" />
      </div>
      <Skeleton className="h-12 w-full rounded-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
