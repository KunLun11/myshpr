import Link from "next/link";

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
    title: "Мастер темы",
    description:
      "Сфера интересов → исследовательский вопрос → тема. Проверка на повтор и на «слишком широко» до отправки учителю.",
  },
  {
    title: "Помощник продукта",
    description:
      "Категория продукта, подсказки и примеры. Понятный результат, который можно показать на защите.",
  },
  {
    title: "Работа над проектом",
    description:
      "Файлы работы, комментарии учителя и чек-листы этапов с прогрессом — без чатов и лишней бюрократии.",
  },
  {
    title: "Дашборд «кто застрял»",
    description:
      "Цветовой статус с причиной, а не только цвет. Учитель видит проблему в сентябре, а не в апреле.",
  },
];

export default function Home() {
  return (
    <div className="flex flex-1 flex-col">
      <header className="border-b border-[var(--border)]">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold">Индивидуальный проект</span>
          <nav className="flex items-center gap-3">
            <Link href="/register" className={buttonVariants({ variant: "ghost", size: "sm" })}>
              Регистрация
            </Link>
            <Link href="/login" className={buttonVariants({ size: "sm" })}>
              Войти
            </Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-16">
        <section className="flex flex-col items-start gap-6">
          <Badge variant="secondary">Пилот · 2026/2027</Badge>
          <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">
            Начать индивидуальный проект вовремя — и не застрять на теме
          </h1>
          <p className="max-w-2xl text-lg text-[var(--muted-foreground)]">
            Приложение помогает ученику 9–11 класса сформулировать тему и определить
            продукт, а учителю — увидеть, кому нужна помощь.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link href="/register" className={buttonVariants({ size: "lg" })}>
              Начать
            </Link>
            <Link href="/login" className={buttonVariants({ variant: "outline", size: "lg" })}>
              У меня есть аккаунт
            </Link>
          </div>
        </section>

        <section className="mt-16 grid gap-4 sm:grid-cols-2">
          {FEATURES.map((feature) => (
            <Card key={feature.title}>
              <CardHeader>
                <CardTitle>{feature.title}</CardTitle>
                <CardDescription>{feature.description}</CardDescription>
              </CardHeader>
              <CardContent />
            </Card>
          ))}
        </section>
      </main>

      <footer className="border-t border-[var(--border)]">
        <div className="mx-auto w-full max-w-5xl px-6 py-6 text-sm text-[var(--muted-foreground)]">
          MVP · Без чатов, оценок и интеграции с журналом.
        </div>
      </footer>
    </div>
  );
}
