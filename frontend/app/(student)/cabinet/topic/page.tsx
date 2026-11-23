import type { Metadata } from "next";
import { Suspense } from "react";

import { TopicWizard } from "@/components/topic-wizard";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { InterestArea, Project } from "@/types/api";

export const metadata: Metadata = { title: "Мастер темы" };

export default function TopicPage() {
  return (
    <Suspense fallback={<WizardSkeleton />}>
      <TopicContent />
    </Suspense>
  );
}

async function TopicContent() {
  await requireUser();
  const [project, areas] = await Promise.all([
    serverApiGet<Project | null>("/me/project"),
    serverApiGet<InterestArea[]>("/reference/interest-areas"),
  ]);

  if (areas === null) {
    return (
      <Alert>
        Не удалось загрузить справочник сфер интересов. Обновите страницу или войдите заново.
      </Alert>
    );
  }

  return <TopicWizard initialProject={project} areas={areas} />;
}

function WizardSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-9 w-56" />
        <Skeleton className="h-4 w-full max-w-xl" />
      </div>
      <Skeleton className="h-14 w-full max-w-md rounded-full" />
      <Skeleton className="h-[28rem] w-full" />
    </div>
  );
}
