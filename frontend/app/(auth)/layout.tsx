import { Check, Compass, MessageSquare, ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/brand-mark";
import { ThemeToggle } from "@/components/theme-toggle";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";

const HIGHLIGHTS = [
  { Icon: Compass, text: "Мастер темы подскажет, как сузить идею" },
  { Icon: ShieldCheck, text: "Проверка на повторы до отправки учителю" },
  { Icon: MessageSquare, text: "Комментарии и чек-листы всегда под рукой" },
] as const;

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="px-4 pt-4">
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
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link
              href="/"
              className={buttonVariants({ variant: "ghost", size: "sm" })}
            >
              На главную
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-10 px-4 py-8 sm:px-6 lg:grid-cols-[1.05fr_1fr]">
        <section className="hidden lg:block">
          <div className="glass-sky animate-fade-up relative overflow-hidden rounded-[var(--r-2xl)] p-9">
            <div
              aria-hidden="true"
              className="absolute -right-14 -top-16 size-52 rounded-full bg-sky-gradient opacity-25 blur-3xl"
            />
            <div className="relative space-y-6">
              <Badge variant="secondary">
                <Check className="size-3.5 text-[var(--success)]" aria-hidden="true" />
                Пилот · 2026/2027
              </Badge>
              <h1 className="font-display text-4xl leading-tight">
                Твой проект начинается <span className="text-gradient">здесь</span>
              </h1>
              <p className="max-w-[42ch] text-[var(--muted-foreground)]">
                Спокойный интерфейс, понятные шаги и поддержка учителя — без
                бесконечных вкладок и чатов.
              </p>
              <ul className="space-y-3">
                {HIGHLIGHTS.map((item) => {
                  const Icon = item.Icon;
                  return (
                    <li key={item.text} className="flex items-start gap-3 text-sm">
                      <span className="grid size-8 shrink-0 place-items-center rounded-xl bg-[var(--primary-soft)] text-[var(--primary)]">
                        <Icon className="size-4" aria-hidden="true" />
                      </span>
                      <span className="pt-1.5">{item.text}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </div>
        </section>

        <div className="mx-auto w-full max-w-md animate-fade-up">{children}</div>
      </main>
    </div>
  );
}

