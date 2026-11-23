import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { ReviewQueue } from "@/components/review-queue";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { Submission } from "@/types/api";

export const metadata: Metadata = { title: "Проверка тем" };

export default function SubmissionsPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-3xl font-semibold tracking-tight">Проверка тем</h1>
          <Link href="/teacher/topics" className={buttonVariants({ variant: "outline", size: "sm" })}>
            Реестр тем
          </Link>
        </div>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Заявки из ваших классов. Проверки повтора и ширины уже выполнены — остаётся
          решение и комментарий ученику.
        </p>
      </header>

      <Suspense fallback={<QueueSkeleton />}>
        <SubmissionsContent />
      </Suspense>
    </div>
  );
}

async function SubmissionsContent() {
  await requireUser();
  const queue = await serverApiGet<Submission[]>("/teacher/submissions?status=submitted");

  if (queue === null) {
    return <Alert>Не удалось загрузить очередь. Обновите страницу или войдите заново.</Alert>;
  }

  return <ReviewQueue initialItems={queue} />;
}

function QueueSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-4">
      <Skeleton className="h-64 w-full" />
      <Skeleton className="h-64 w-full" />
    </div>
  );
}
