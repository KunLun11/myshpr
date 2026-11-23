import type { Metadata } from "next";
import { ArrowRight, CalendarClock, Compass } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { ProjectStatusBadge } from "@/components/project-status-badge";
import { ProjectStepper } from "@/components/project-stepper";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { buttonVariants } from "@/components/ui/button";
import { Alert } from "@/components/ui/alert";
import { requireUser } from "@/lib/auth";
import { firstName, formatDate } from "@/lib/format";
import { serverApiGet } from "@/lib/server-api";
import type { Project } from "@/types/api";

export const metadata: Metadata = { title: "Мой проект" };

export default function CabinetPage() {
  return (
    <Suspense fallback={<CabinetSkeleton />}>
      <CabinetContent />
    </Suspense>
  );
}

async function CabinetContent() {
  const user = await requireUser();
  const project = await serverApiGet<Project | null>("/me/project");
  const status = project?.status ?? "idea";
  const next = nextStep(project);

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        {user.school ? (
          <p className="text-sm text-[var(--muted-foreground)]">{user.school.name}</p>
        ) : null}
        <h1 className="text-3xl font-semibold tracking-tight">
          Здравствуйте, {firstName(user.full_name)}
        </h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Здесь виден ваш индивидуальный проект: тема, продукт и работа над этапами.
        </p>
      </header>

      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <CardTitle>Мой проект</CardTitle>
              <ProjectStatusBadge status={status} />
            </div>
            <CardDescription>
              {project?.topic?.title ??
                "Текущий этап отмечен цветом, иконкой и текстом."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ProjectStepper current={status} />
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Compass className="size-4 text-[var(--primary)]" aria-hidden="true" />
                {next.title}
              </CardTitle>
              <CardDescription>{next.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <ol className="space-y-2 text-sm text-[var(--muted-foreground)]">
                {next.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ol>
              <Link
                href={next.href}
                className={buttonVariants({ variant: next.linkVariant ?? "default" })}
              >
                {next.linkLabel}
                <ArrowRight aria-hidden="true" />
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CalendarClock className="size-4 text-[var(--primary)]" aria-hidden="true" />
                Ближайшая контрольная точка
              </CardTitle>
              <CardDescription>
                {project?.next_checkpoint
                  ? "Дата, к которой школа ждёт нужный этап проекта."
                  : "Все точки пройдены или школа пока не назначила даты."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {project?.next_checkpoint ? (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <p className="font-medium">{project.next_checkpoint.title}</p>
                    <p className="text-sm text-[var(--muted-foreground)]">
                      {formatDate(project.next_checkpoint.due_at)}
                      {project.next_checkpoint.overdue
                        ? " · срок прошёл"
                        : ` · осталось ${project.next_checkpoint.days_left} дн.`}
                    </p>
                  </div>
                  {project.next_checkpoint.overdue ? (
                    <Alert variant="warning">
                      Срок этой точки уже прошёл. Отметьте выполненные пункты чек-листа
                      или напишите учителю через комментарии к работе.
                    </Alert>
                  ) : null}
                </div>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CalendarClock className="size-4 text-[var(--primary)]" aria-hidden="true" />
                Класс
              </CardTitle>
              <CardDescription>
                {user.class
                  ? `${user.class.label} · ${user.class.academic_year_name ?? "текущий учебный год"}`
                  : "Класс не назначен. Обратитесь к учителю."}
              </CardDescription>
            </CardHeader>
            <CardContent />
          </Card>
        </div>
      </div>
    </div>
  );
}

interface NextStep {
  title: string;
  description: string;
  bullets: string[];
  linkLabel: string;
  href: string;
  linkVariant?: "default" | "outline";
}

function nextStep(project: Project | null): NextStep {
  if (!project) {
    return {
      title: "Сформулировать тему проекта",
      description: "Мастер подскажет, как выбрать сферу, вопрос и тему.",
      bullets: [
        "1. Выберите сферу интересов.",
        "2. Сформулируйте исследовательский вопрос.",
        "3. Предложите тему и отправьте её учителю.",
      ],
      linkLabel: "Открыть мастер темы",
      href: "/cabinet/topic",
    };
  }
  if (!project.interest_area) {
    return {
      title: "Выберите сферу интересов",
      description: "Сфера задаёт направление, но не ограничивает вашу тему.",
      bullets: ["Начните с области, которая вам ближе.", "Дальше — вопрос и формулировка темы."],
      linkLabel: "Открыть мастер темы",
      href: "/cabinet/topic",
    };
  }
  if (!project.research_question) {
    return {
      title: "Сформулируйте исследовательский вопрос",
      description: "Вопрос помогает не потеряться в слишком широкой теме.",
      bullets: [
        "Начните со слов «как», «почему» или «влияет ли».",
        "Добавьте объект: место, группу или период.",
      ],
      linkLabel: "Перейти к вопросу",
      href: "/cabinet/topic",
    };
  }
  if (!project.topic) {
    return {
      title: "Предложите формулировку темы",
      description: "Проверка покажет повторы и подскажет, как сузить тему.",
      bullets: [
        "Тема — от 4 до 20 слов.",
        "Проверка не даст отправить тему, которая уже занята.",
      ],
      linkLabel: "Сформулировать тему",
      href: "/cabinet/topic",
    };
  }
  if (project.status === "topic_submitted") {
    return {
      title: "Тема на проверке",
      description: "Учитель увидит заявку в очереди и примет решение.",
      bullets: [
        `Тема: «${project.topic.title}».`,
        "Пока идёт проверка, формулировку изменить нельзя.",
      ],
      linkLabel: "Посмотреть статус",
      href: "/cabinet/topic",
      linkVariant: "outline",
    };
  }
  if (project.status === "topic_approved" || project.status === "product_draft") {
    return {
      title: "Определите продукт",
      description: "Выберите формат результата и опишите, что покажете на защите.",
      bullets: [
        `Тема: «${project.topic.title}».`,
        "Продукт — это модель, исследование, приложение, видео или другой результат.",
        "После сохранения откроется работа над проектом.",
      ],
      linkLabel: "Выбрать продукт",
      href: "/cabinet/product",
    };
  }
  if (
    project.status === "product_defined" ||
    project.status === "in_progress" ||
    project.status === "ready_for_defense" ||
    project.status === "defended"
  ) {
    return {
      title: "Работа над проектом",
      description: "Отмечайте пункты чек-листа, загружайте файлы и читайте комментарии.",
      bullets: [
        "Чек-лист покажет, что уже сделано и что осталось.",
        "Файлы и комментарии учителя собраны в одном разделе.",
      ],
      linkLabel: "Открыть работу",
      href: "/cabinet/work",
      linkVariant: "outline",
    };
  }
  return {
    title: "Доработайте тему",
    description: project.topic.review_comment
      ? "Учитель оставил комментарий к заявке."
      : "Проверьте формулировку и отправьте тему снова.",
    bullets: project.topic.review_comment
      ? [`Комментарий учителя: ${project.topic.review_comment}`]
      : ["Исправьте замечания в мастере темы.", "Отправьте заявку повторно."],
    linkLabel: "Открыть мастер темы",
    href: "/cabinet/topic",
  };
}

function CabinetSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-8">
      <div className="space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-full max-w-xl" />
      </div>
      <div className="grid gap-6 lg:grid-cols-[1.15fr_1fr]">
        <Skeleton className="h-96 w-full" />
        <div className="space-y-6">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    </div>
  );
}
