import type { Metadata } from "next";
import { Suspense } from "react";

import { ProductPlanner } from "@/components/product-planner";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { ProductCategory, ProductState, Project } from "@/types/api";

export const metadata: Metadata = { title: "Продукт проекта" };

export default function ProductPage() {
  return (
    <Suspense fallback={<ProductSkeleton />}>
      <ProductContent />
    </Suspense>
  );
}

async function ProductContent() {
  await requireUser();
  const [project, categories, product] = await Promise.all([
    serverApiGet<Project | null>("/me/project"),
    serverApiGet<ProductCategory[]>("/reference/product-categories"),
    serverApiGet<ProductState>("/me/project/product"),
  ]);

  if (categories === null) {
    return (
      <Alert>
        Не удалось загрузить категории продукта. Обновите страницу или войдите заново.
      </Alert>
    );
  }

  return (
    <ProductPlanner
      project={project}
      categories={categories}
      initialProduct={product}
    />
  );
}

function ProductSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <div className="space-y-3">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-9 w-72" />
        <Skeleton className="h-4 w-full max-w-xl" />
      </div>
      <Skeleton className="h-72 w-full" />
      <Skeleton className="h-56 w-full" />
    </div>
  );
}
