"use client";

import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Clock,
  Compass,
  HelpCircle,
  Info,
  Lightbulb,
  LoaderCircle,
  Send,
  Sparkles,
  WifiOff,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ProjectStatusBadge } from "@/components/project-status-badge";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  CheckLevel,
  CheckMessage,
  InterestArea,
  Project,
  ProjectPatchResponse,
  TopicCheck,
} from "@/types/api";

const STEPS = [
  { key: "area", label: "Сфера" },
  { key: "question", label: "Вопрос" },
  { key: "title", label: "Тема" },
] as const;

const LOCKED_STATUSES = new Set([
  "topic_submitted",
  "topic_approved",
  "product_draft",
  "product_defined",
  "in_progress",
  "ready_for_defense",
  "defended",
  "archived",
]);

const QUESTION_EXAMPLES = [
  "Как шум в школьной столовой влияет на внимание учеников 9 класса?",
  "Почему ученики реже пользуются школьной библиотекой в старших классах?",
  "Как качество воды в реке Москве меняется за последние три года?",
];

function wordCount(value: string): number {
  return value.trim() ? value.trim().split(/\s+/).length : 0;
}

function apiErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "RATE_LIMITED") {
      return "Слишком много проверок подряд. Подождите минуту и попробуйте снова.";
    }
    return error.message;
  }
  return "Не удалось связаться с сервером. Проверьте соединение и попробуйте ещё раз.";
}

function initialStep(project: Project | null): number {
  if (!project?.interest_area) {
    return 0;
  }
  if (!project.research_question) {
    return 1;
  }
  return 2;
}

const LEVEL_META: Record<
  CheckLevel,
  { label: string; variant: "success" | "warning" | "danger"; Icon: typeof Check }
> = {
  ok: { label: "Всё в порядке", variant: "success", Icon: CheckCircle2 },
  warn: { label: "Есть замечания", variant: "warning", Icon: AlertTriangle },
  block: { label: "Нужно исправить", variant: "danger", Icon: X },
};

function LevelBadge({ level, label }: { level: CheckLevel; label?: string }) {
  const meta = LEVEL_META[level];
  const Icon = meta.Icon;
  return (
    <Badge variant={meta.variant}>
      <Icon className="mr-1 size-3.5" aria-hidden="true" />
      {label ?? meta.label}
    </Badge>
  );
}

export function TopicWizard({
  initialProject,
  areas,
}: {
  initialProject: Project | null;
  areas: InterestArea[];
}) {
  const [project, setProject] = useState<Project | null>(initialProject);
  const [interestAreaId, setInterestAreaId] = useState(initialProject?.interest_area?.id ?? "");
  const [question, setQuestion] = useState(initialProject?.research_question ?? "");
  const [title, setTitle] = useState(initialProject?.topic?.title ?? "");
  const [step, setStep] = useState(() => initialStep(initialProject));
  const [warnings, setWarnings] = useState<CheckMessage[]>([]);
  const [saveState, setSaveState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [check, setCheck] = useState<TopicCheck | null>(null);
  const [checking, setChecking] = useState(false);
  const [checkError, setCheckError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [offline, setOffline] = useState(false);

  const status = project?.status ?? "idea";
  const locked = LOCKED_STATUSES.has(status);
  const firstRender = useRef(true);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener("online", update);
    window.addEventListener("offline", update);
    return () => {
      window.removeEventListener("online", update);
      window.removeEventListener("offline", update);
    };
  }, []);

  useEffect(() => {
    if (locked || offline) {
      return;
    }
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }

    setSaveState("saving");
    const timer = window.setTimeout(async () => {
      try {
        const response = await api.patch<ProjectPatchResponse>("/me/project", {
          interest_area_id: interestAreaId || null,
          research_question: question,
          topic_title: title.trim() ? title : null,
        });
        setProject(response.project);
        setWarnings(response.warnings);
        setSaveState("saved");
      } catch (error) {
        setSaveState("error");
        setWarnings([{ field: "general", message: apiErrorMessage(error) }]);
      }
    }, 800);

    return () => window.clearTimeout(timer);
  }, [interestAreaId, question, title, locked, offline]);

  useEffect(() => {
    if (locked || step !== 2 || offline) {
      return;
    }
    const trimmed = title.trim();
    if (!trimmed) {
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setChecking(true);
      try {
        const result = await api.post<TopicCheck>("/me/project/topic/check", {
          title: trimmed,
          research_question: question.trim() || null,
        });
        if (!cancelled) {
          setCheck(result);
          setCheckError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setCheckError(apiErrorMessage(error));
        }
      } finally {
        if (!cancelled) {
          setChecking(false);
        }
      }
    }, 600);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [title, question, step, locked, offline]);

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await api
        .patch<ProjectPatchResponse>("/me/project", {
          interest_area_id: interestAreaId || null,
          research_question: question,
          topic_title: title,
        })
        .catch(() => undefined);
      const updated = await api.post<Project>("/me/project/topic/submit", {
        title,
        research_question: question,
      });
      setProject(updated);
      setCheck(null);
    } catch (error) {
      setSubmitError(apiErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  }

  if (locked) {
    return <TopicStatusView project={project!} />;
  }

  const selectedArea = areas.find((area) => area.id === interestAreaId) ?? null;
  const rejectedComment =
    project?.topic?.status === "rejected" ? project.topic.review_comment : null;
  const canGoNext = step === 0 ? Boolean(interestAreaId) : question.trim().length > 0;
  const canSubmit =
    Boolean(check?.can_submit) && !checking && !submitting && !offline && saveState !== "saving";

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Мастер темы</h1>
          <ProjectStatusBadge status={status} />
        </div>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Три шага: сфера интересов, исследовательский вопрос и формулировка темы.
          Черновик сохраняется автоматически.
        </p>
      </header>

      {offline ? (
        <Alert variant="warning" className="flex items-start gap-2">
          <WifiOff className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
          <span>
            Нет соединения. Изменения не сохранятся, пока сеть не вернётся — текст останется в
            форме.
          </span>
        </Alert>
      ) : null}

      {rejectedComment ? (
        <Alert variant="warning">
          <p className="font-medium">Учитель вернул тему на доработку</p>
          <p className="mt-1">{rejectedComment}</p>
        </Alert>
      ) : null}

      <ol className="flex flex-wrap items-center gap-2" aria-label="Шаги мастера">
        {STEPS.map((item, index) => {
          const done = index < step;
          const active = index === step;
          return (
            <li key={item.key}>
              <button
                type="button"
                onClick={() => setStep(index)}
                aria-current={active ? "step" : undefined}
                className={cn(
                  "flex min-h-11 items-center gap-2 rounded-full px-4 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
                  active
                    ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                    : "bg-[var(--muted)] text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
                )}
              >
                {done ? (
                  <Check className="size-4" aria-hidden="true" />
                ) : (
                  <span className="text-xs font-semibold">{index + 1}</span>
                )}
                {item.label}
              </button>
            </li>
          );
        })}
      </ol>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            {step === 0 ? (
              <>
                <Compass className="size-5 text-[var(--primary)]" aria-hidden="true" />
                Сфера интересов
              </>
            ) : step === 1 ? (
              <>
                <HelpCircle className="size-5 text-[var(--primary)]" aria-hidden="true" />
                Исследовательский вопрос
              </>
            ) : (
              <>
                <Sparkles className="size-5 text-[var(--primary)]" aria-hidden="true" />
                Формулировка темы
              </>
            )}
          </CardTitle>
          <CardDescription>
            {step === 0
              ? "Выберите область, которая вам ближе. Это подскажет направление, но не ограничивает."
              : step === 1
                ? "Вопрос задаёт фокус проекта. Начните со слов «как», «почему», «что» или «влияет ли»."
                : "Тема — короткое название проекта. Проверка подскажет, если тема слишком широкая или уже занята."}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          {step === 0 ? (
            <fieldset>
              <legend className="sr-only">Сфера интересов</legend>
              <div className="grid gap-3 sm:grid-cols-2">
                {areas.map((area) => {
                  const selected = area.id === interestAreaId;
                  return (
                    <label
                      key={area.id}
                      className={cn(
                        "flex cursor-pointer flex-col gap-1 rounded-[var(--radius-md)] border p-4 transition-colors focus-within:ring-2 focus-within:ring-[var(--ring)]",
                        selected
                          ? "border-[var(--primary)] bg-[var(--info-soft)]"
                          : "border-[var(--border)] bg-[var(--background)] hover:bg-[var(--muted)]",
                      )}
                    >
                      <input
                        type="radio"
                        name="interest-area"
                        value={area.id}
                        checked={selected}
                        onChange={() => setInterestAreaId(area.id)}
                        className="sr-only"
                      />
                      <span className="flex items-center gap-2 font-medium">
                        {selected ? (
                          <CheckCircle2
                            className="size-4 text-[var(--primary)]"
                            aria-hidden="true"
                          />
                        ) : (
                          <CircleDotPlaceholder />
                        )}
                        {area.name}
                      </span>
                      {area.description ? (
                        <span className="text-sm text-[var(--muted-foreground)]">
                          {area.description}
                        </span>
                      ) : null}
                    </label>
                  );
                })}
              </div>
              {areas.length === 0 ? (
                <Alert variant="info">
                  Справочник сфер пока пуст. Попросите администратора школы заполнить его.
                </Alert>
              ) : null}
            </fieldset>
          ) : null}

          {step === 1 ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="research-question" className="text-sm font-medium">
                  Исследовательский вопрос
                </label>
                <textarea
                  id="research-question"
                  value={question}
                  onChange={(event) => {
                    setQuestion(event.target.value);
                    setCheck(null);
                    setChecking(true);
                  }}
                  rows={4}
                  maxLength={500}
                  placeholder="Например: как шум в школьной столовой влияет на внимание учеников 9 класса?"
                  className="w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm outline-none transition-colors placeholder:text-[var(--muted-foreground)] focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)]"
                />
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-[var(--muted-foreground)]">
                  <span>{wordCount(question)} слов · от 6 до 40</span>
                  {question.trim() && !question.trim().endsWith("?") ? (
                    <span className="text-[var(--warning)]">Вопрос должен заканчиваться «?»</span>
                  ) : null}
                </div>
              </div>

              <div className="rounded-[var(--radius-md)] bg-[var(--muted)] p-4">
                <p className="flex items-center gap-2 text-sm font-medium">
                  <Lightbulb className="size-4" aria-hidden="true" />
                  Примеры хороших вопросов
                </p>
                <ul className="mt-2 space-y-1 text-sm text-[var(--muted-foreground)]">
                  {QUESTION_EXAMPLES.map((example) => (
                    <li key={example}>{example}</li>
                  ))}
                </ul>
              </div>

              {warnings.length > 0 ? (
                <Alert variant="warning">
                  <ul className="space-y-1">
                    {warnings.map((warning) => (
                      <li key={warning.message}>{warning.message}</li>
                    ))}
                  </ul>
                </Alert>
              ) : null}
            </div>
          ) : null}

          {step === 2 ? (
            <div className="space-y-5">
              <div className="space-y-2">
                <label htmlFor="topic-title" className="text-sm font-medium">
                  Тема проекта
                </label>
                <input
                  id="topic-title"
                  value={title}
                  onChange={(event) => {
                    setTitle(event.target.value);
                    setCheck(null);
                    setChecking(true);
                  }}
                  maxLength={300}
                  placeholder="Например: Сравнение качества воды в реке Москве за 2024 год"
                  className="h-11 w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 text-sm outline-none transition-colors placeholder:text-[var(--muted-foreground)] focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--card)]"
                />
                <p className="text-xs text-[var(--muted-foreground)]">
                  {wordCount(title)} слов · от 4 до 20
                  {selectedArea ? ` · сфера «${selectedArea.name}»` : ""}
                </p>
              </div>

              <ChecksPanel
                check={title.trim() ? check : null}
                checking={checking}
                error={checkError}
                hasTitle={title.trim().length > 0}
              />

              {submitError ? <Alert>{submitError}</Alert> : null}

              {check && !check.can_submit ? (
                <Alert variant="info">
                  Исправьте замечания выше — после этого кнопка «Отправить» станет активной.
                </Alert>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-[var(--muted-foreground)]" aria-live="polite">
          {saveState === "saving" ? (
            <>
              <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
              Сохраняем…
            </>
          ) : saveState === "saved" ? (
            <>
              <Check className="size-4" aria-hidden="true" />
              Черновик сохранён
            </>
          ) : saveState === "error" ? (
            <>
              <AlertTriangle className="size-4" aria-hidden="true" />
              Не удалось сохранить
            </>
          ) : (
            <>Черновик сохраняется автоматически</>
          )}
        </div>

        <div className="flex gap-2">
          {step > 0 ? (
            <Button variant="outline" onClick={() => setStep(step - 1)}>
              <ArrowLeft aria-hidden="true" />
              Назад
            </Button>
          ) : null}

          {step < 2 ? (
            <Button onClick={() => setStep(step + 1)} disabled={!canGoNext}>
              Далее
              <ArrowRight aria-hidden="true" />
            </Button>
          ) : (
            <Button onClick={handleSubmit} disabled={!canSubmit}>
              {submitting ? (
                <LoaderCircle className="animate-spin" aria-hidden="true" />
              ) : (
                <Send aria-hidden="true" />
              )}
              {submitting ? "Отправляем…" : "Отправить учителю"}
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

function CircleDotPlaceholder() {
  return (
    <span
      aria-hidden="true"
      className="size-4 rounded-full border border-[var(--muted-foreground)]"
    />
  );
}

function ChecksPanel({
  check,
  checking,
  error,
  hasTitle,
}: {
  check: TopicCheck | null;
  checking: boolean;
  error: string | null;
  hasTitle: boolean;
}) {
  if (!hasTitle) {
    return (
      <div className="rounded-[var(--radius-md)] border border-dashed border-[var(--border)] p-4 text-sm text-[var(--muted-foreground)]">
        Начните вводить тему — проверка повторов и ширины появится здесь.
      </div>
    );
  }

  if (error) {
    return <Alert>{error}</Alert>;
  }

  if (checking && !check) {
    return (
      <div
        aria-busy="true"
        className="flex items-center gap-2 rounded-[var(--radius-md)] bg-[var(--muted)] p-4 text-sm text-[var(--muted-foreground)]"
      >
        <LoaderCircle className="size-4 animate-spin" aria-hidden="true" />
        Проверяем формулировку…
      </div>
    );
  }

  if (!check) {
    return null;
  }

  return (
    <div className="space-y-4" aria-live="polite">
      {check.errors.length > 0 ? (
        <Alert>
          <p className="font-medium">Что нужно исправить</p>
          <ul className="mt-1 list-inside list-disc space-y-1">
            {check.errors.map((item) => (
              <li key={item.message}>{item.message}</li>
            ))}
          </ul>
        </Alert>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-[var(--radius-md)] border border-[var(--border)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Повтор темы</h3>
            <LevelBadge
              level={check.duplicate.level}
              label={
                check.duplicate.exact
                  ? "Точный повтор"
                  : check.duplicate.level === "ok"
                    ? "Повторов нет"
                    : check.duplicate.level === "warn"
                      ? "Похожая тема"
                      : "Тема занята"
              }
            />
          </div>
          {check.duplicate.matches.length > 0 ? (
            <ul className="mt-3 space-y-2 text-sm">
              {check.duplicate.matches.slice(0, 4).map((match) => (
                <li key={`${match.source}-${match.id}`} className="space-y-0.5">
                  <p className="font-medium">{match.title}</p>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    {match.source === "registry" ? "В реестре" : "На проверке"} · сходство{" "}
                    {Math.round(match.score * 100)}%
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-[var(--muted-foreground)]">
              В реестре и среди заявок этого года такой темы нет.
            </p>
          )}
        </section>

        <section className="rounded-[var(--radius-md)] border border-[var(--border)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Ширина темы</h3>
            <LevelBadge
              level={check.broadness.level}
              label={`${check.broadness.score} из 100`}
            />
          </div>
          {check.broadness.reasons.length > 0 ? (
            <ul className="mt-3 space-y-1 text-sm text-[var(--muted-foreground)]">
              {check.broadness.reasons.map((reason) => (
                <li key={reason} className="flex gap-2">
                  <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                  {reason}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-[var(--muted-foreground)]">
              Тема достаточно конкретная: есть объект и уточнение.
            </p>
          )}
          {check.broadness.level !== "ok" && check.broadness.suggestions.length > 0 ? (
            <div className="mt-3">
              <p className="flex items-center gap-1 text-sm font-medium">
                <Lightbulb className="size-3.5" aria-hidden="true" />
                Как сузить
              </p>
              <ul className="mt-1 list-inside list-disc text-sm text-[var(--muted-foreground)]">
                {check.broadness.suggestions.map((suggestion) => (
                  <li key={suggestion}>{suggestion}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function TopicStatusView({ project }: { project: Project }) {
  const submitted = project.status === "topic_submitted";
  const approved = !submitted;
  const Icon = approved ? CheckCircle2 : Clock;
  const title = project.topic?.title || "Тема проекта";
  const question = project.topic?.research_question || project.research_question || "—";

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">
            {approved ? "Тема утверждена" : "Тема на проверке"}
          </h1>
          <ProjectStatusBadge status={project.status} />
        </div>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          {submitted
            ? "Учитель получил заявку и увидит её в очереди на проверку. Менять формулировку пока нельзя."
            : project.status === "topic_approved"
              ? "Учитель утвердил тему — она попала в реестр школы. Следующий этап — выбор продукта."
              : "Тема утверждена и хранится в реестре школы."}
        </p>
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Icon
              className={cn(
                "size-5",
                approved ? "text-[var(--success)]" : "text-[var(--warning)]",
              )}
              aria-hidden="true"
            />
            {approved ? "Утверждённая тема" : "Отправленная заявка"}
          </CardTitle>
          <CardDescription>
            {project.interest_area ? `Сфера: ${project.interest_area.name}` : "Сфера не указана"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">Тема</p>
            <p className="text-lg font-medium">{title}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
              Исследовательский вопрос
            </p>
            <p className="text-sm">{question}</p>
          </div>
          {approved && project.topic_approved_at ? (
            <p className="text-sm text-[var(--muted-foreground)]">
              Утверждена{" "}
              {new Date(project.topic_approved_at).toLocaleDateString("ru-RU", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </p>
          ) : null}
          {project.topic?.review_comment ? (
            <Alert variant="info">
              <p className="font-medium">Комментарий учителя</p>
              <p className="mt-1">{project.topic.review_comment}</p>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <div className="flex flex-wrap gap-2">
        <Link href="/cabinet" className={buttonVariants({ variant: "outline" })}>
          <ArrowLeft aria-hidden="true" />
          Мой проект
        </Link>
      </div>
    </div>
  );
}
