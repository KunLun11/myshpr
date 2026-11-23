"use client";

import {
  AlertTriangle,
  Archive,
  BadgeCheck,
  Boxes,
  Check,
  CheckCircle2,
  Circle,
  Clock,
  Compass,
  Flag,
  Hammer,
  Lightbulb,
  LoaderCircle,
  MinusCircle,
  Package,
  Pencil,
  PlayCircle,
  Rocket,
  RotateCcw,
  Send,
  SkipForward,
  Sparkles,
  Trophy,
} from "lucide-react";
import { useId, useState, type CSSProperties } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type {
  ChecklistItemState,
  ChecklistState,
  ProjectChecklist,
  ProjectStatus,
} from "@/types/api";

const STATUS_META: Record<
  ChecklistState,
  { label: string; variant: "success" | "info" | "warning" | "secondary" | "danger"; Icon: typeof Circle }
> = {
  pending: { label: "Впереди", variant: "secondary", Icon: Circle },
  in_progress: { label: "В процессе", variant: "info", Icon: Clock },
  done: { label: "Сделано", variant: "success", Icon: CheckCircle2 },
  verified: { label: "Проверено", variant: "success", Icon: BadgeCheck },
  skipped: { label: "Пропуск", variant: "secondary", Icon: MinusCircle },
};

const STAGE_ICONS: Record<ProjectStatus, typeof Circle> = {
  idea: Lightbulb,
  topic_draft: Pencil,
  topic_submitted: Send,
  topic_approved: BadgeCheck,
  product_draft: Package,
  product_defined: Boxes,
  in_progress: Hammer,
  ready_for_defense: Rocket,
  defended: Trophy,
  archived: Archive,
};

const RESOLVED_STATUSES = new Set<ChecklistState>(["done", "verified", "skipped"]);

function isStageResolved(stage: ProjectChecklist["stages"][number]) {
  return stage.items.length > 0 && stage.items.every((item) => RESOLVED_STATUSES.has(item.status));
}

function encouragement(percent: number) {
  if (percent >= 100) return "Ура! Все обязательные шаги пройдены — можно готовиться к защите.";
  if (percent >= 75) return "Финиш уже близко! Осталось совсем немного.";
  if (percent >= 50) return "Больше половины пути позади. Так держать!";
  if (percent >= 25) return "Отличный старт! Ты на верном пути.";
  return "Каждый маленький шаг приближает тебя к защите проекта.";
}

function ProgressRing({ percent }: { percent: number }) {
  const size = 112;
  const stroke = 10;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(100, Math.max(0, percent));
  const offset = circumference - (clamped / 100) * circumference;
  const gradientId = `roadmap-ring-${useId().replace(/[^a-zA-Z0-9_-]/g, "")}`;

  return (
    <div
      className="roadmap-ring"
      style={{ width: size, height: size }}
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={clamped}
      aria-label="Готовность чек-листа"
    >
      <svg viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="var(--sky-blue)" />
            <stop offset="55%" stopColor="var(--primary)" />
            <stop offset="100%" stopColor="var(--mint)" />
          </linearGradient>
        </defs>
        <circle
          className="roadmap-ring__track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={stroke}
        />
        <circle
          className="roadmap-ring__value"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={`url(#${gradientId})`}
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="roadmap-ring__label font-display">{clamped}%</span>
    </div>
  );
}

function RoadmapStat({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Circle;
  label: string;
  value: string;
  tone: "iris" | "mint" | "warning";
}) {
  return (
    <div className="roadmap-stat">
      <span className={`roadmap-stat__icon roadmap-stat__icon--${tone}`}>
        <Icon className="size-3.5" aria-hidden="true" />
      </span>
      <span className="flex flex-col leading-tight">
        <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-[var(--muted-foreground)]">
          {label}
        </span>
        <span className="text-sm font-semibold text-[var(--foreground)]">{value}</span>
      </span>
    </div>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Не удалось обновить чек-лист. Проверьте соединение.";
}

export function ChecklistPanel({
  initialChecklist,
  mode,
}: {
  initialChecklist: ProjectChecklist;
  mode: "student" | "teacher";
}) {
  const [checklist, setChecklist] = useState(initialChecklist);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    const next = await api.get<ProjectChecklist>(
      mode === "teacher"
        ? `/teacher/projects/${initialChecklist.project_id}/checklist`
        : "/me/project/checklist",
    );
    setChecklist(next);
  }

  async function studentUpdate(item: ChecklistItemState, status: ChecklistState) {
    setPendingId(item.id);
    setError(null);
    try {
      await api.patch<ChecklistItemState>(
        `/me/project/checklist/${item.checklist_item_id}`,
        { status },
      );
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPendingId(null);
    }
  }

  async function staffTransition(item: ChecklistItemState, action: "verify" | "skip") {
    setPendingId(item.id);
    setError(null);
    try {
      await api.post<ChecklistItemState>(
        `/teacher/checklist-states/${item.id}/${action}`,
        { comment: null },
      );
      await refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPendingId(null);
    }
  }

  const { progress, overdue_count } = checklist;
  const totalItems = checklist.stages.reduce((sum, stage) => sum + stage.total_count, 0);
  const doneItems = checklist.stages.reduce((sum, stage) => sum + stage.done_count, 0);
  const remainingRequired = Math.max(progress.required - progress.done, 0);
  const currentStageIndex = checklist.stages.findIndex((stage) => !isStageResolved(stage));
  const finishReached = progress.percent >= 100;
  const finishSide =
    checklist.stages.length % 2 === 0 ? "roadmap-stage--left" : "roadmap-stage--right";

  return (
    <div className="space-y-5">
      <section className="glass-sky relative overflow-hidden rounded-[var(--r-2xl)] p-5 sm:p-7">
        <div className="roadmap-hero__glow" aria-hidden="true" />
        <div className="relative flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4 sm:gap-5">
            <ProgressRing percent={progress.percent} />
            <div className="min-w-0 space-y-1.5">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[var(--primary)]">
                Твой маршрут
              </p>
              <h2 className="font-display text-xl leading-snug sm:text-2xl">
                Путь к защите проекта
              </h2>
              <p className="max-w-[42ch] text-sm text-[var(--muted-foreground)]">
                {encouragement(progress.percent)}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2 lg:justify-end">
            <RoadmapStat
              icon={Flag}
              label="Обязательные"
              value={`${progress.done} из ${progress.required}`}
              tone="iris"
            />
            <RoadmapStat
              icon={Sparkles}
              label="Пройдено шагов"
              value={`${doneItems} из ${totalItems}`}
              tone="mint"
            />
            {overdue_count > 0 ? (
              <RoadmapStat
                icon={AlertTriangle}
                label="Просрочено"
                value={`${overdue_count}`}
                tone="warning"
              />
            ) : (
              <RoadmapStat
                icon={CheckCircle2}
                label="Дедлайны"
                value="Всё вовремя"
                tone="mint"
              />
            )}
          </div>
        </div>
      </section>

      {error ? <Alert>{error}</Alert> : null}

      {checklist.stages.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 p-8 text-center">
            <span className="icon-tile tile-sky">
              <Compass className="size-5" aria-hidden="true" />
            </span>
            <div className="space-y-1">
              <CardTitle className="text-lg">Карта пока пустая</CardTitle>
              <CardDescription>
                Администратор школы ещё не добавил шаги для этого учебного года. Как только они
                появятся, здесь вырастет твой маршрут.
              </CardDescription>
            </div>
          </CardContent>
        </Card>
      ) : (
        <ol
          className="roadmap"
          style={{ "--roadmap-fill": `${progress.percent}%` } as CSSProperties}
        >
          {checklist.stages.map((stage, index) => {
            const complete = isStageResolved(stage);
            const current = index === currentStageIndex;
            const StageIcon = STAGE_ICONS[stage.stage] ?? Flag;
            const stagePercent =
              stage.total_count > 0
                ? Math.round((stage.done_count / stage.total_count) * 100)
                : 0;
            return (
              <li
                key={stage.stage}
                className={`roadmap-stage ${
                  index % 2 === 0 ? "roadmap-stage--left" : "roadmap-stage--right"
                }`}
              >
                <div
                  className={`roadmap-node ${
                    complete ? "roadmap-node--done" : current ? "roadmap-node--current" : ""
                  }`}
                  aria-hidden="true"
                >
                  {complete ? <Check /> : <StageIcon />}
                </div>
                <Card className={`roadmap-card ${current ? "roadmap-card--current" : ""}`}>
                  <CardHeader className="p-4 pb-3 sm:p-5 sm:pb-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[var(--muted-foreground)]">
                          Этап {index + 1}
                          {current ? " · сейчас" : ""}
                        </p>
                        <CardTitle className="text-base">{stage.title}</CardTitle>
                      </div>
                      <Badge
                        variant={complete ? "success" : current ? "info" : "secondary"}
                        className="shrink-0"
                      >
                        {complete ? <Check className="mr-1 size-3" aria-hidden="true" /> : null}
                        {stage.done_count} из {stage.total_count}
                      </Badge>
                    </div>
                    <div
                      role="progressbar"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={stagePercent}
                      aria-label={`Готовность этапа «${stage.title}»`}
                      className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-[var(--muted)]"
                    >
                      <div
                        className="h-full rounded-full bg-sky-gradient transition-[width] duration-500"
                        style={{ width: `${stagePercent}%` }}
                      />
                    </div>
                  </CardHeader>
                  <CardContent className="p-4 pt-0 sm:p-5 sm:pt-0">
                    <ul className="space-y-2.5">
                      {stage.items.map((item) => (
                        <li key={item.id}>
                          <ChecklistRow
                            item={item}
                            mode={mode}
                            pending={pendingId === item.id}
                            onStudentUpdate={studentUpdate}
                            onStaffTransition={staffTransition}
                          />
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              </li>
            );
          })}
          <li className={`roadmap-stage ${finishSide}`}>
            <div
              className={`roadmap-node ${finishReached ? "roadmap-node--done" : ""}`}
              aria-hidden="true"
            >
              <Trophy />
            </div>
            <div
              className={`roadmap-finish roadmap-card ${
                finishReached ? "roadmap-finish--done" : ""
              }`}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold">Финиш: защита проекта</p>
                <p className="text-xs opacity-80">
                  {finishReached
                    ? "Все обязательные шаги пройдены. Ты готов!"
                    : `До финиша осталось обязательных шагов: ${remainingRequired}.`}
                </p>
              </div>
              {finishReached ? (
                <Sparkles className="size-5 shrink-0" aria-hidden="true" />
              ) : (
                <Flag className="size-5 shrink-0 opacity-70" aria-hidden="true" />
              )}
            </div>
          </li>
        </ol>
      )}
    </div>
  );
}

function ChecklistRow({
  item,
  mode,
  pending,
  onStudentUpdate,
  onStaffTransition,
}: {
  item: ChecklistItemState;
  mode: "student" | "teacher";
  pending: boolean;
  onStudentUpdate: (item: ChecklistItemState, status: ChecklistState) => void;
  onStaffTransition: (item: ChecklistItemState, action: "verify" | "skip") => void;
}) {
  const meta = STATUS_META[item.status];
  const Icon = meta.Icon;
  const done = item.status === "done" || item.status === "verified";
  const active = item.status === "in_progress";
  const locked = item.status === "verified" || item.status === "skipped";
  const canAct = !locked;
  const stepTone = item.overdue
    ? "roadmap-step--overdue"
    : done
      ? "roadmap-step--done"
      : active
        ? "roadmap-step--active"
        : "";
  const iconTone = item.overdue
    ? "roadmap-step__icon--overdue"
    : done
      ? "roadmap-step__icon--done"
      : active
        ? "roadmap-step__icon--active"
        : "";

  return (
    <div className={`roadmap-step ${stepTone}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex min-w-0 items-start gap-3">
          <span className={`roadmap-step__icon ${iconTone}`}>
            <Icon className="size-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 space-y-1.5">
            <p className="flex flex-wrap items-center gap-2 text-sm font-semibold leading-snug">
              {item.title}
              {item.is_required ? (
                <Badge variant="secondary" className="text-[10px]">
                  обязательный
                </Badge>
              ) : null}
              {item.overdue ? (
                <Badge variant="warning">
                  <AlertTriangle className="mr-1 size-3" aria-hidden="true" />
                  просрочен
                </Badge>
              ) : null}
            </p>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-[var(--muted-foreground)]">
              <Badge variant={meta.variant}>{meta.label}</Badge>
              {item.due_at ? <span>до {formatDate(item.due_at)}</span> : null}
              {item.verified_at ? <span>проверено {formatDate(item.verified_at)}</span> : null}
            </div>
            {item.description ? (
              <p className="text-sm text-[var(--muted-foreground)]">{item.description}</p>
            ) : null}
            {item.comment ? (
              <p className="rounded-[var(--r-sm)] bg-[var(--info-soft)] px-2.5 py-1.5 text-sm text-[var(--info-soft-foreground)]">
                Комментарий учителя: {item.comment}
              </p>
            ) : null}
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
        {pending ? (
          <LoaderCircle className="size-4 animate-spin text-[var(--muted-foreground)]" aria-hidden="true" />
        ) : null}
        {mode === "student" && canAct && item.status === "pending" ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onStudentUpdate(item, "in_progress")}
            disabled={pending}
          >
            <PlayCircle aria-hidden="true" />
            Начать
          </Button>
        ) : null}
        {mode === "student" && canAct ? (
          <Button
            size="sm"
            variant={done ? "outline" : "default"}
            onClick={() => onStudentUpdate(item, done ? "in_progress" : "done")}
            disabled={pending}
          >
            {done ? <RotateCcw aria-hidden="true" /> : <CheckCircle2 aria-hidden="true" />}
            {done ? "Вернуть в работу" : "Готово"}
          </Button>
        ) : null}
        {mode === "teacher" &&
        (item.status === "done" || item.status === "in_progress") ? (
          <Button size="sm" onClick={() => onStaffTransition(item, "verify")} disabled={pending}>
            <BadgeCheck aria-hidden="true" />
            Подтвердить
          </Button>
        ) : null}
        {mode === "teacher" && item.status === "pending" ? (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onStaffTransition(item, "skip")}
            disabled={pending}
          >
            <SkipForward aria-hidden="true" />
            Пропустить
          </Button>
        ) : null}
        </div>
      </div>
    </div>
  );
}
