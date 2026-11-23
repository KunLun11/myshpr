"use client";

import {
  AlertOctagon,
  AlertTriangle,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  MessageSquare,
  Paperclip,
  RefreshCw,
  Search,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ProjectStatusBadge, projectStatusMeta } from "@/components/project-status-badge";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { formatDate, formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type {
  ClassDashboard,
  DashboardStudent,
  ProjectStatus,
  StatusReason,
  TrafficLight,
} from "@/types/api";

const LIGHT_META: Record<
  TrafficLight,
  {
    label: string;
    variant: "danger" | "warning" | "success";
    Icon: typeof AlertTriangle;
    bubble: string;
    surface: string;
  }
> = {
  red: {
    label: "Застрял",
    variant: "danger",
    Icon: AlertOctagon,
    bubble: "bg-[var(--destructive-soft)] text-[var(--destructive-soft-foreground)]",
    surface: "border-[var(--destructive)]/25",
  },
  yellow: {
    label: "Нужно внимание",
    variant: "warning",
    Icon: AlertTriangle,
    bubble: "bg-[var(--warning-soft)] text-[var(--warning-soft-foreground)]",
    surface: "border-[var(--warning)]/25",
  },
  green: {
    label: "В порядке",
    variant: "success",
    Icon: CheckCircle2,
    bubble: "bg-[var(--success-soft)] text-[var(--success-soft-foreground)]",
    surface: "border-[var(--success)]/20",
  },
};

const COLOR_FILTERS: { value: "" | TrafficLight; label: string }[] = [
  { value: "", label: "Все" },
  { value: "red", label: "Красные" },
  { value: "yellow", label: "Жёлтые" },
  { value: "green", label: "Зелёные" },
];

const PROJECT_STATUSES: ProjectStatus[] = [
  "idea",
  "topic_draft",
  "topic_submitted",
  "topic_approved",
  "product_draft",
  "product_defined",
  "in_progress",
  "ready_for_defense",
  "defended",
];

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Не удалось загрузить дашборд. Проверьте соединение и попробуйте снова.";
}

function progressPercent(done: number, total: number): number {
  return total > 0 ? Math.round((done / total) * 100) : 0;
}

function ReasonLine({ reason }: { reason: StatusReason }) {
  const Icon =
    reason.severity === "red"
      ? AlertOctagon
      : reason.severity === "yellow"
        ? AlertTriangle
        : CheckCircle2;
  return (
    <li className="flex items-start gap-2 text-sm">
      <Icon
        className={cn(
          "mt-0.5 size-4 shrink-0",
          reason.severity === "red"
            ? "text-[var(--destructive)]"
            : reason.severity === "yellow"
              ? "text-[var(--warning)]"
              : "text-[var(--success)]",
        )}
        aria-hidden="true"
      />
      <span>{reason.label}</span>
    </li>
  );
}

function StudentCard({ student }: { student: DashboardStudent }) {
  const meta = LIGHT_META[student.color];
  const Icon = meta.Icon;
  const percent = progressPercent(student.checklist_done, student.checklist_total);

  return (
    <article
      className={cn(
        "rounded-[var(--radius)] border bg-[var(--card)] p-5 shadow-[var(--shadow-soft)]",
        meta.surface,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <span
            className={cn(
              "mt-0.5 flex size-10 shrink-0 items-center justify-center rounded-full",
              meta.bubble,
            )}
          >
            <Icon className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 space-y-1.5">
            <h3 className="truncate text-base font-semibold tracking-tight">
              {student.student_full_name}
            </h3>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant={meta.variant}>
                <Icon className="mr-1 size-3.5" aria-hidden="true" />
                {meta.label}
              </Badge>
              {student.status === "no_project" ? (
                <Badge variant="secondary">Проект не создан</Badge>
              ) : (
                <ProjectStatusBadge status={student.status} />
              )}
            </div>
          </div>
        </div>
        {student.project_id ? (
          <Link
            href={`/teacher/projects/${student.project_id}`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Открыть проект
            <ArrowRight aria-hidden="true" />
          </Link>
        ) : null}
      </div>

      {student.topic_title ? (
        <p className="mt-3 line-clamp-2 text-sm text-[var(--muted-foreground)]">
          Тема: {student.topic_title}
        </p>
      ) : null}

      <ul className="mt-3 space-y-1.5">
        {student.reasons.map((reason) => (
          <ReasonLine key={`${reason.code}-${reason.label}`} reason={reason} />
        ))}
      </ul>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-xs text-[var(--muted-foreground)]">Последняя активность</dt>
          <dd className="mt-0.5 font-medium">
            {student.last_activity_at
              ? student.inactive_days === 0
                ? "Сегодня"
                : `${student.inactive_days} дн. назад`
              : "Нет данных"}
          </dd>
          {student.last_activity_at ? (
            <dd className="text-xs text-[var(--muted-foreground)]">
              {formatDateTime(student.last_activity_at)}
            </dd>
          ) : null}
        </div>
        <div>
          <dt className="text-xs text-[var(--muted-foreground)]">Чек-лист</dt>
          <dd className="mt-0.5 font-medium">
            {student.checklist_done} из {student.checklist_total}
            {student.checklist_overdue > 0 ? (
              <Badge variant="danger" className="ml-2 align-middle">
                {student.checklist_overdue} просрочено
              </Badge>
            ) : null}
          </dd>
          {student.checklist_total > 0 ? (
            <div
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={percent}
              aria-label={`Чек-лист ${student.student_full_name}`}
              className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--muted)]"
            >
              <div
                className="h-full rounded-full bg-[var(--primary)] transition-[width] duration-300"
                style={{ width: `${percent}%` }}
              />
            </div>
          ) : null}
        </div>
        <div>
          <dt className="text-xs text-[var(--muted-foreground)]">Файлы</dt>
          <dd className="mt-0.5 flex items-center gap-1.5 font-medium">
            <Paperclip className="size-3.5" aria-hidden="true" />
            {student.files_count}
            {student.has_final_file ? (
              <Badge variant="success" className="ml-1">
                Итоговый есть
              </Badge>
            ) : null}
          </dd>
        </div>
        <div>
          <dt className="text-xs text-[var(--muted-foreground)]">Ближайшая точка</dt>
          <dd className="mt-0.5 flex items-start gap-1.5 font-medium">
            <CalendarClock className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
            {student.next_checkpoint ? (
              <span>
                {student.next_checkpoint.title}
                <span className="block text-xs font-normal text-[var(--muted-foreground)]">
                  {formatDate(student.next_checkpoint.due_at)} ·{" "}
                  {student.next_checkpoint.overdue
                    ? "просрочена"
                    : `${student.next_checkpoint.days_left} дн.`}
                </span>
              </span>
            ) : (
              <span className="text-[var(--muted-foreground)]">Нет активных точек</span>
            )}
          </dd>
        </div>
      </dl>

      {student.last_comment_excerpt ? (
        <div className="mt-4 flex items-start gap-2 rounded-[var(--radius-md)] bg-[var(--muted)] px-3 py-2 text-sm">
          <MessageSquare
            className="mt-0.5 size-4 shrink-0 text-[var(--muted-foreground)]"
            aria-hidden="true"
          />
          <p className="min-w-0">
            <span className="text-[var(--muted-foreground)]">Последний комментарий: </span>
            «{student.last_comment_excerpt}»
          </p>
        </div>
      ) : null}
    </article>
  );
}

export function StuckDashboard({
  classId,
  initial,
}: {
  classId: string;
  initial: ClassDashboard;
}) {
  const [data, setData] = useState<ClassDashboard>(initial);
  const [color, setColor] = useState<"" | TrafficLight>("");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const firstRender = useRef(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    if (color) {
      params.set("color", color);
    }
    if (status) {
      params.set("status", status);
    }
    if (query.trim()) {
      params.set("q", query.trim());
    }
    const suffix = params.size > 0 ? `?${params.toString()}` : "";
    try {
      const next = await api.get<ClassDashboard>(
        `/teacher/classes/${classId}/dashboard${suffix}`,
      );
      setData(next);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [classId, color, status, query]);

  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    const handle = setTimeout(() => {
      void load();
    }, 300);
    return () => clearTimeout(handle);
  }, [load]);

  const { summary } = data;
  const redShare = summary.total > 0 ? Math.round((summary.red / summary.total) * 100) : 0;

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <Users className="size-4" aria-hidden="true" />
              Всего учеников
            </CardDescription>
            <CardTitle className="text-3xl">{summary.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <AlertOctagon className="size-4 text-[var(--destructive)]" aria-hidden="true" />
              Застряли
            </CardDescription>
            <CardTitle className="text-3xl">{summary.red}</CardTitle>
            <p className="text-xs text-[var(--muted-foreground)]">{redShare}% класса</p>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <AlertTriangle className="size-4 text-[var(--warning)]" aria-hidden="true" />
              Нужно внимание
            </CardDescription>
            <CardTitle className="text-3xl">{summary.yellow}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-[var(--success)]" aria-hidden="true" />
              В порядке
            </CardDescription>
            <CardTitle className="text-3xl">{summary.green}</CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative w-full sm:w-64">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-[var(--muted-foreground)]"
            aria-hidden="true"
          />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Поиск по имени"
            aria-label="Поиск ученика по имени"
            className="pl-9"
          />
        </div>
        <div role="group" aria-label="Фильтр по статусу" className="flex flex-wrap gap-1">
          {COLOR_FILTERS.map((filter) => (
            <Button
              key={filter.value || "all"}
              type="button"
              size="sm"
              variant={color === filter.value ? "default" : "outline"}
              aria-pressed={color === filter.value}
              onClick={() => setColor(filter.value)}
            >
              {filter.label}
            </Button>
          ))}
        </div>
        <select
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          aria-label="Фильтр по статусу проекта"
          className="h-11 rounded-md border border-[var(--input)] bg-[var(--background)] px-3 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        >
          <option value="">Все статусы</option>
          {PROJECT_STATUSES.map((value) => (
            <option key={value} value={value}>
              {projectStatusMeta(value).label}
            </option>
          ))}
          <option value="no_project">Проект не создан</option>
        </select>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          onClick={() => void load()}
          disabled={loading}
        >
          <RefreshCw aria-hidden="true" className={loading ? "animate-spin" : undefined} />
          Обновить
        </Button>
        <span className="text-xs text-[var(--muted-foreground)]" aria-live="polite">
          {loading ? "Обновляем…" : `Показано: ${data.students.length}`}
        </span>
      </div>

      {error ? <Alert>{error}</Alert> : null}

      {data.students.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Никого не нашли</CardTitle>
            <CardDescription>
              Попробуйте снять фильтры или изменить запрос. Если в классе ещё нет
              учеников, они появятся после регистрации по коду приглашения.
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className={cn("space-y-3 transition-opacity", loading ? "opacity-60" : "opacity-100")}>
          {data.students.map((student) => (
            <StudentCard key={student.student_id} student={student} />
          ))}
        </div>
      )}
    </div>
  );
}
