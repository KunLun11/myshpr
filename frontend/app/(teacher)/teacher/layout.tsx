import { Suspense } from "react";
import type { ReactNode } from "react";

import { AppShell, AppShellSkeleton } from "@/components/app-shell";
import { requireRole } from "@/lib/auth";

export const instant = false;

export default function TeacherLayout({ children }: { children: ReactNode }) {
  return (
    <Suspense fallback={<AppShellSkeleton />}>
      <ProtectedShell>{children}</ProtectedShell>
    </Suspense>
  );
}

async function ProtectedShell({ children }: { children: ReactNode }) {
  const user = await requireRole("teacher");
  return <AppShell user={user}>{children}</AppShell>;
}
