import {
  ArrowRight,
  Check,
  ClipboardCheck,
  Compass,
  GraduationCap,
  MessageSquare,
  PackageCheck,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import Link from "next/link";

import { BrandMark } from "@/components/brand-mark";
import { ProjectStatusBadge } from "@/components/project-status-badge";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const FEATURES = [
  {
    Icon: Compass,
    tile: "tile-iris",
    title: "Мастер темы",
    description:
      "Сфера интересов → исследовательский вопрос → тема. Проверка на повтор и на «слишком широко» до отправки учителю.",
  },
  {
    Icon: PackageCheck,
    tile: "tile-sky",
    title: "Помощник продукта",
    description:
      "Категория продукта, подсказки и примеры. Понятный результат, который можно показать на защите.",
  },
  {
    Icon: MessageSquare,
    tile: "tile-mint",
    title: "Работа без хаоса",
    description:
      "Файлы работы, комментарии учителя и чек-листы этапов с прогрессом — без чатов и лишней бюрократии.",
  },
  {
    Icon: Users,
    tile: "tile-sunset",
    title: "Дашборд «кто застрял»",
    description:
      "Статус с причиной, а не только цвет. Учитель видит проблему в сентябре, а не в апреле.",
  },
] as const;

const STEPS = [
  {
    title: "Выбери сферу",
    description:
      "Начни с того, что тебе действительно интересно: игры, экология, музыка, спорт, технологии.",
  },
  {
    title: "Сформулируй тему",
    description:
      "Мастер задаст вопросы и проверит тему на повторы и лишнюю широту — без страха ошибиться.",
  },
  {
    title: "Дойди до защиты",
    description:
      "Чек-лист, файлы и комментарии учителя всегда под рукой. Следующий шаг понятен.",
  },
] as const;

const PREVIEW_STEPS = [
  { label: "Черновик темы", state: "done" },
  { label: "На проверке", state: "done" },
  { label: "Тема утверждена", state: "active" },
  { label: "Выбор продукта", state: "todo" },
] as const;

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="sticky top-0 z-30 px-3 pt-3 sm:px-4">
        <div className="glass mx-auto flex w-full max-w-6xl items-center justify-between gap-3 rounded-[var(--r-xl)] px-3 py-2.5 sm:px-5">
          <Link
            href="/"
            className="flex min-w-0 items-center gap-2.5 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          >
            <BrandMark className="size-9" />
            <span className="truncate font-display text-sm font-semibold tracking-tight sm:text-base">
              <span className="sm:hidden">Проект</span>
              <span className="hidden sm:inline">Индивидуальный проект</span>
            </span>
          </Link>
          <nav className="flex items-center gap-1 sm:gap-2">
            <a
              href="#features"
              className="hidden min-h-11 items-center rounded-full px-3.5 text-sm font-semibold text-[var(--muted-foreground)] transition-colors hover:text-[var(--foreground)] md:inline-flex"
            >
              Возможности
            </a>
            <a
              href="#how"
              className="hidden min-h-11 items-center rounded-full px-3.5 text-sm font-semibold text-[var(--muted-foreground)] transition-colors hover:text-[var(--foreground)] md:inline-flex"
            >
              Как это работает
            </a>
            <ThemeToggle />
            <span className="hidden sm:block">
              <Link
                href="/login"
                className={buttonVariants({ variant: "ghost", size: "sm" })}
              >
                Войти
              </Link>
            </span>
            <Link href="/register" className={buttonVariants({ size: "sm" })}>
              Начать
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl flex-1 px-4 pb-16 pt-10 sm:px-6 sm:pt-16">
        <section className="grid items-center gap-12 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="animate-fade-up space-y-7">
            <Badge variant="secondary" className="px-3 py-1.5 text-[13px]">
              <Sparkles className="size-3.5 text-[var(--primary)]" aria-hidden="true" />
              Пилот · 2026/2027
            </Badge>

            <h1 className="text-[length:var(--type-display)]">
              Начни проект{" "}
              <span className="text-gradient">вовремя</span> — и не застрянь на теме
            </h1>

            <p className="max-w-[58ch] text-lg leading-relaxed text-[var(--muted-foreground)]">
              Приложение для учеников 9–11 класса: помогает выбрать тему, придумать
              продукт и дойти до защиты. Учитель видит, кому нужна помощь, ещё в
              сентябре.
            </p>

            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/register"
                className={buttonVariants({ variant: "default", size: "lg" })}
              >
                Начать проект
                <ArrowRight aria-hidden="true" />
              </Link>
              <Link
                href="/login"
                className={buttonVariants({ variant: "outline", size: "lg" })}
              >
                У меня есть аккаунт
              </Link>
            </div>

            <ul className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-[var(--muted-foreground)]">
              {[
                "9–11 класс",
                "Без чатов и оценок",
                "Работает на слабых ноутбуках",
              ].map((item) => (
                <li key={item} className="flex items-center gap-1.5">
                  <span className="grid size-5 place-items-center rounded-full bg-[var(--success-soft)] text-[var(--success-soft-foreground)]">
                    <Check className="size-3" aria-hidden="true" />
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="relative mx-auto w-full max-w-md lg:max-w-none">
            <div
              aria-hidden="true"
              className="absolute -inset-8 -z-10 rounded-[3rem] bg-sky-gradient opacity-20 blur-3xl"
            />
            <Card className="glass-sky animate-pop-in overflow-hidden rounded-[var(--r-2xl)] p-0">
              <div className="flex items-center justify-between gap-3 border-b border-[var(--glass-border)] px-5 py-4">
                <div className="flex items-center gap-2.5">
                  <span className="grid size-9 place-items-center rounded-xl bg-[var(--primary-soft)] text-[var(--primary)]">
                    <GraduationCap className="size-[1.15rem]" aria-hidden="true" />
                  </span>
                  <div>
                    <p className="font-display text-sm font-semibold">Мой проект</p>
                    <p className="text-xs text-[var(--muted-foreground)]">
                      Личный кабинет ученика
                    </p>
                  </div>
                </div>
                <ProjectStatusBadge status="topic_approved" />
              </div>

              <div className="space-y-5 px-5 py-5">
                <div className="space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[var(--muted-foreground)]">
                    Тема
                  </p>
                  <p className="font-display text-lg leading-snug">
                    Как видеоигры влияют на внимание школьников
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-xs text-[var(--muted-foreground)]">
                    <span>Прогресс</span>
                    <span>3 из 9 этапов</span>
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-full bg-[var(--muted)]">
                    <div
                      className="h-full rounded-full bg-primary-gradient"
                      style={{ width: "34%" }}
                    />
                  </div>
                </div>

                <ul className="space-y-2.5">
                  {PREVIEW_STEPS.map((step) => (
                    <li key={step.label} className="flex items-center gap-2.5 text-sm">
                      <span
                        className={
                          step.state === "done"
                            ? "grid size-6 place-items-center rounded-full bg-[var(--success-soft)] text-[var(--success-soft-foreground)]"
                            : step.state === "active"
                              ? "grid size-6 place-items-center rounded-full bg-primary-gradient text-[var(--primary-foreground)] shadow-[var(--shadow-glow)]"
                              : "grid size-6 place-items-center rounded-full border border-[var(--border)] text-[var(--muted-foreground)]"
                        }
                      >
                        {step.state === "done" ? (
                          <Check className="size-3.5" aria-hidden="true" />
                        ) : step.state === "active" ? (
                          <Sparkles className="size-3.5" aria-hidden="true" />
                        ) : (
                          <span className="size-1.5 rounded-full bg-current" />
                        )}
                      </span>
                      <span
                        className={
                          step.state === "active"
                            ? "font-semibold"
                            : step.state === "todo"
                              ? "text-[var(--muted-foreground)]"
                              : ""
                        }
                      >
                        {step.label}
                      </span>
                    </li>
                  ))}
                </ul>

                <div className="flex items-center gap-3 rounded-[var(--r-md)] bg-[var(--glass-bg-strong)] p-3.5">
                  <span className="icon-tile tile-mint size-10 rounded-xl">
                    <ClipboardCheck className="size-[1.15rem]" aria-hidden="true" />
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm font-semibold">Следующий шаг</p>
                    <p className="text-xs text-[var(--muted-foreground)]">
                      Выбрать категорию продукта
                    </p>
                  </div>
                  <ArrowRight
                    className="ml-auto size-4 text-[var(--muted-foreground)]"
                    aria-hidden="true"
                  />
                </div>
              </div>
            </Card>

            <div className="mt-4 flex flex-wrap items-center justify-center gap-2">
              <div className="glass float-slow flex items-center gap-2 rounded-full px-3.5 py-2 text-xs font-semibold">
                <ShieldCheck className="size-4 text-[var(--success)]" aria-hidden="true" />
                Тема проверена
              </div>
              <div className="glass float-slower flex items-center gap-2 rounded-full px-3.5 py-2 text-xs font-semibold">
                <MessageSquare className="size-4 text-[var(--primary)]" aria-hidden="true" />
                Комментарий учителя
              </div>
            </div>
          </div>
        </section>

        <section id="features" className="scroll-mt-28 pt-24">
          <div className="max-w-[60ch] space-y-3">
            <Badge variant="secondary">Возможности</Badge>
            <h2 className="font-display text-3xl leading-tight sm:text-4xl">
              Всё, что нужно, чтобы не потеряться
            </h2>
            <p className="text-[var(--muted-foreground)]">
              Один спокойный интерфейс вместо пяти вкладок и чата с классом.
            </p>
          </div>

          <div className="stagger-list mt-8 grid gap-4 sm:grid-cols-2">
            {FEATURES.map((feature) => {
              const Icon = feature.Icon;
              return (
                <Card key={feature.title} interactive className="group">
                  <CardHeader className="gap-4">
                    <span className={`icon-tile ${feature.tile}`}>
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <div className="space-y-1.5">
                      <CardTitle>{feature.title}</CardTitle>
                      <CardDescription>{feature.description}</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent />
                </Card>
              );
            })}
          </div>
        </section>

        <section id="how" className="scroll-mt-28 pt-24">
          <div className="max-w-[60ch] space-y-3">
            <Badge variant="secondary">Как это работает</Badge>
            <h2 className="font-display text-3xl leading-tight sm:text-4xl">
              Три понятных шага
            </h2>
          </div>

          <div className="stagger-list mt-8 grid gap-4 md:grid-cols-3">
            {STEPS.map((step, index) => (
              <Card key={step.title} className="relative overflow-hidden">
                <div
                  aria-hidden="true"
                  className="absolute -right-8 -top-10 size-28 rounded-full bg-sky-gradient opacity-15 blur-2xl"
                />
                <CardHeader className="gap-3">
                  <span className="grid size-10 place-items-center rounded-full bg-primary-gradient font-display text-sm font-semibold text-[var(--primary-foreground)] shadow-[var(--shadow-glow)]">
                    {index + 1}
                  </span>
                  <CardTitle>{step.title}</CardTitle>
                  <CardDescription>{step.description}</CardDescription>
                </CardHeader>
              </Card>
            ))}
          </div>
        </section>

        <section className="pt-24">
          <div className="glass-sky relative overflow-hidden rounded-[var(--r-2xl)] px-6 py-10 sm:px-10 sm:py-12">
            <div
              aria-hidden="true"
              className="absolute -right-16 -top-20 size-64 rounded-full bg-sky-gradient opacity-25 blur-3xl"
            />
            <div className="relative flex flex-col items-start gap-6 md:flex-row md:items-center md:justify-between">
              <div className="max-w-[52ch] space-y-3">
                <h2 className="font-display text-3xl leading-tight sm:text-4xl">
                  Начни свой проект <span className="text-gradient">сегодня</span>
                </h2>
                <p className="text-[var(--muted-foreground)]">
                  Регистрация по коду класса занимает минуту. Дальше мастер сам
                  подскажет следующий шаг.
                </p>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link
                  href="/register"
                  className={buttonVariants({ variant: "default", size: "lg" })}
                >
                  Создать аккаунт
                  <ArrowRight aria-hidden="true" />
                </Link>
                <Link
                  href="/login"
                  className={buttonVariants({ variant: "outline", size: "lg" })}
                >
                  Войти
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="mt-auto px-4 pb-8 sm:px-6">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-3 border-t border-[var(--border)] pt-6 text-sm text-[var(--muted-foreground)] sm:flex-row sm:items-center sm:justify-between">
          <span className="flex items-center gap-2">
            <BrandMark className="size-7" />
            Индивидуальный проект
          </span>
          <span>MVP · без чатов, оценок и интеграции с журналом</span>
        </div>
      </footer>
    </div>
  );
}

