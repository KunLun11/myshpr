import { Suspense } from "react";
import type { ReactNode } from "react";
import type { Metadata } from "next";

import { AppShell, AppShellSkeleton } from "@/components/app-shell";
import { requireRole } from "@/lib/auth";

export const instant = false;
export const metadata: Metadata = {
  title: { default: "Админка", template: "%s · Админка" },
  robots: { index: false, follow: false },
};

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<AppShellSkeleton />}>
      <ProtectedShell>{children}</ProtectedShell>
    </Suspense>
  );
}

async function ProtectedShell({ children }: { children: ReactNode }) {
  const user = await requireRole("school_admin");
  return <AppShell user={user}>{children}</AppShell>;
}
