import type { Metadata } from "next";
import { Suspense } from "react";

import { AdminReferences } from "@/components/admin/admin-references";
import { Alert } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { serverApiGet } from "@/lib/server-api";
import type { AdminInterestArea, AdminProductCategory } from "@/types/api";

export const metadata: Metadata = { title: "Справочники" };
export const instant = false;

export default function AdminReferencesPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Справочники</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Сферы интересов и категории продукта. Изменения сразу видны ученикам и учителям после
          обновления страницы.
        </p>
      </header>
      <Suspense fallback={<ReferencesSkeleton />}>
        <ReferencesSection />
      </Suspense>
    </div>
  );
}

async function ReferencesSection() {
  const user = await requireUser();
  const [areas, categories] = await Promise.all([
    serverApiGet<AdminInterestArea[]>("/admin/interest-areas"),
    serverApiGet<AdminProductCategory[]>("/admin/product-categories"),
  ]);

  if (areas === null || categories === null) {
    return <Alert>Не удалось загрузить справочники. Обновите страницу.</Alert>;
  }

  return (
    <AdminReferences
      areas={areas}
      categories={categories}
      canEdit={user.role === "super_admin"}
    />
  );
}

function ReferencesSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite" className="space-y-6">
      <Skeleton className="h-96 w-full" />
      <Skeleton className="h-96 w-full" />
    </div>
  );
}
