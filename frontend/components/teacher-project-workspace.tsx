"use client";

import {
  ClipboardCheck,
  LayoutDashboard,
  MessageSquare,
  PackageCheck,
  Paperclip,
} from "lucide-react";
import { useState } from "react";

import { ChecklistPanel } from "@/components/checklist-panel";
import { CommentsPanel } from "@/components/comments-panel";
import { FilesPanel } from "@/components/files-panel";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  ProjectChecklist,
  ProjectFile,
  TeacherComment,
  TeacherProject,
} from "@/types/api";

type TabKey = "overview" | "checklist" | "files" | "comments";

const TOPIC_STATUS_LABELS: Record<string, string> = {
  draft: "черновик",
  submitted: "на проверке",
  approved: "утверждена",
  rejected: "отклонена",
  superseded: "заменена",
};

const TABS: { key: TabKey; label: string; Icon: typeof LayoutDashboard }[] = [
  { key: "overview", label: "Обзор", Icon: LayoutDashboard },
  { key: "checklist", label: "Чек-лист", Icon: ClipboardCheck },
  { key: "files", label: "Файлы", Icon: Paperclip },
  { key: "comments", label: "Комментарии", Icon: MessageSquare },
];

export function TeacherProjectWorkspace({
  project,
  checklist,
  files,
  comments,
}: {
  project: TeacherProject;
  checklist: ProjectChecklist;
  files: ProjectFile[];
  comments: TeacherComment[];
}) {
  const [active, setActive] = useState<TabKey>("overview");

  const counts: Record<TabKey, string | null> = {
    overview: null,
    checklist: `${checklist.progress.percent}%`,
    files: String(files.length),
    comments: String(comments.length),
  };

  return (
    <div className="space-y-4">
      <div
        role="tablist"
        aria-label="Разделы карточки проекта"
        className="flex flex-wrap gap-1 rounded-full bg-[var(--muted)] p-1"
      >
        {TABS.map((tab) => {
          const selected = active === tab.key;
          const Icon = tab.Icon;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              id={`teacher-tab-${tab.key}`}
              aria-selected={selected}
              aria-controls={`teacher-panel-${tab.key}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => setActive(tab.key)}
              onKeyDown={(event) => {
                if (event.key !== "ArrowRight" && event.key !== "ArrowLeft") {
                  return;
                }
                event.preventDefault();
                const index = TABS.findIndex((item) => item.key === active);
                const nextIndex =
                  event.key === "ArrowRight"
                    ? (index + 1) % TABS.length
                    : (index - 1 + TABS.length) % TABS.length;
                const next = TABS[nextIndex];
                setActive(next.key);
                document.getElementById(`teacher-tab-${next.key}`)?.focus();
              }}
              className={cn(
                "inline-flex min-h-11 flex-1 items-center justify-center gap-2 rounded-full px-4 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
                selected
                  ? "bg-[var(--card)] text-[var(--foreground)] shadow-[var(--shadow-soft)]"
                  : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
              )}
            >
              <Icon className="size-4" aria-hidden="true" />
              {tab.label}
              {counts[tab.key] ? (
                <span className="rounded-full bg-[var(--background)] px-2 py-0.5 text-xs text-[var(--muted-foreground)]">
                  {counts[tab.key]}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id={`teacher-panel-${active}`}
        aria-labelledby={`teacher-tab-${active}`}
        tabIndex={0}
        className="focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
      >
        {active === "overview" ? (
          <Overview project={project} checklist={checklist} />
        ) : active === "checklist" ? (
          <ChecklistPanel initialChecklist={checklist} mode="teacher" />
        ) : active === "files" ? (
          <FilesPanel initialFiles={files} mode="teacher" />
        ) : (
          <CommentsPanel
            initialComments={comments}
            mode="teacher"
            projectId={project.id}
          />
        )}
      </div>
    </div>
  );
}

function Overview({
  project,
  checklist,
}: {
  project: TeacherProject;
  checklist: ProjectChecklist;
}) {
  return (
    <div className="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Тема и вопрос</CardTitle>
          <CardDescription>
            Тема утверждается отдельно; здесь виден текущий черновик.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {project.topic_title ? (
            <>
              <p className="font-medium">{project.topic_title}</p>
              {project.research_question ? (
                <p className="text-sm text-[var(--muted-foreground)]">
                  {project.research_question}
                </p>
              ) : null}
              {project.topic_status ? (
                <Badge variant="secondary">
                  Заявка: {TOPIC_STATUS_LABELS[project.topic_status] ?? project.topic_status}
                </Badge>
              ) : null}
            </>
          ) : (
            <p className="text-sm text-[var(--muted-foreground)]">
              Ученик ещё не сформулировал тему.
            </p>
          )}
          <p className="text-xs text-[var(--muted-foreground)]">
            Последняя активность: {formatDateTime(project.last_activity_at)}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <PackageCheck className="size-5 text-[var(--primary)]" aria-hidden="true" />
            Продукт
          </CardTitle>
          <CardDescription>
            {project.product_defined_at
              ? `Определён ${formatDate(project.product_defined_at)}`
              : "Пока не определён"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          {project.product_category_name ? (
            <>
              <p className="font-medium">{project.product_category_name}</p>
              {project.product_description ? (
                <p className="text-[var(--muted-foreground)]">{project.product_description}</p>
              ) : null}
              {project.product_brief?.defense_plan ? (
                <p>
                  <span className="font-medium">На защите: </span>
                  {project.product_brief.defense_plan}
                </p>
              ) : null}
              {project.product_brief?.audience ? (
                <p>
                  <span className="font-medium">Для кого: </span>
                  {project.product_brief.audience}
                </p>
              ) : null}
            </>
          ) : (
            <p className="text-[var(--muted-foreground)]">
              Продукт появится после того, как ученик выберет категорию и опишет результат.
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-lg">Чек-лист</CardTitle>
          <CardDescription>
            Обязательные пункты: {checklist.progress.done} из {checklist.progress.required}.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={checklist.progress.percent}
            aria-label="Готовность чек-листа"
            className="h-2.5 w-full overflow-hidden rounded-full bg-[var(--muted)]"
          >
            <div
              className="h-full rounded-full bg-[var(--primary)] transition-[width] duration-300"
              style={{ width: `${checklist.progress.percent}%` }}
            />
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge variant="success">{checklist.progress.percent}% закрыто</Badge>
            {checklist.overdue_count > 0 ? (
              <Badge variant="warning">{checklist.overdue_count} просрочено</Badge>
            ) : (
              <Badge variant="secondary">Без просрочек</Badge>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
