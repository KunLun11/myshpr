import type { Metadata } from "next";
import { CalendarCheck2, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { Suspense } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { RegistryTopic } from "@/types/api";

export const metadata: Metadata = { title: "Реестр тем" };

export default function RegistryPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Реестр тем</h1>
          <Link
            href="/teacher/submissions"
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            Проверка тем
          </Link>
        </div>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Утверждённые темы ваших классов. По этому реестру проверяются повторы новых заявок.
        </p>
      </header>

      <Suspense fallback={<RegistrySkeleton />}>
        <RegistryContent />
      </Suspense>
    </div>
  );
}

async function RegistryContent() {
  await requireUser();
  const topics = await serverApiGet<RegistryTopic[]>("/teacher/topics");

  if (topics === null) {
    return <Alert>Не удалось загрузить реестр. Обновите страницу или войдите заново.</Alert>;
  }

  if (topics.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CalendarCheck2 className="size-5 text-[var(--primary)]" aria-hidden="true" />
            Пока пусто
          </CardTitle>
          <CardDescription>
            Утверждённые темы появятся здесь и сразу начнут участвовать в проверке повторов.
          </CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {topics.map((topic) => (
        <Card key={topic.id}>
          <CardHeader>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="space-y-1">
                <CardTitle className="flex items-center gap-2 text-base">
                  <CheckCircle2
                    className="size-4 text-[var(--success)]"
                    aria-hidden="true"
                  />
                  {topic.title}
                </CardTitle>
                <CardDescription>
                  {topic.author_full_name ?? "Ученик"}
                  {topic.interest_area_name ? ` · ${topic.interest_area_name}` : ""}
                </CardDescription>
              </div>
              <Badge variant="secondary">
                {new Date(topic.approved_at).toLocaleDateString("ru-RU", {
                  day: "numeric",
                  month: "long",
                  year: "numeric",
                })}
              </Badge>
            </div>
          </CardHeader>
          {topic.research_question ? (
            <CardContent>
              <p className="text-sm text-[var(--muted-foreground)]">
                {topic.research_question}
              </p>
            </CardContent>
          ) : null}
        </Card>
      ))}
    </div>
  );
}

function RegistrySkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-3">
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
      <Skeleton className="h-28 w-full" />
    </div>
  );
}
