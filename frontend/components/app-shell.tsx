import Link from "next/link";
import type { ReactNode } from "react";

import { LogoutButton } from "@/components/logout-button";
import { NotificationBell } from "@/components/notification-bell";
import { SessionKeeper } from "@/components/session-keeper";
import { ShellNav } from "@/components/shell-nav";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ROLE_LABELS, homeForRole } from "@/lib/roles";
import type { Me } from "@/types/api";

interface AppShellProps {
  user: Me;
  children: ReactNode;
}

export function AppShell({ user, children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col">
      <SessionKeeper />
      <header className="sticky top-0 z-10 border-b border-[var(--border)] bg-[var(--material-bar)] backdrop-blur-xl">
        <div className="mx-auto flex w-full max-w-5xl flex-col gap-2 px-6 py-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <Link
                href={homeForRole(user.role)}
                className="text-base font-semibold tracking-tight"
              >
                Индивидуальный проект
              </Link>
              <Badge variant="secondary" className="hidden sm:inline-flex">
                {ROLE_LABELS[user.role]}
              </Badge>
            </div>
            <div className="flex items-center gap-2 lg:hidden">
              <LogoutButton />
            </div>
          </div>
          <div className="flex min-w-0 items-center gap-2">
            <ShellNav role={user.role} />
            <NotificationBell />
            <span className="hidden max-w-[180px] truncate text-sm text-[var(--muted-foreground)] xl:inline">
              {user.full_name}
            </span>
            <div className="hidden lg:block">
              <LogoutButton />
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">{children}</main>
    </div>
  );
}

export function AppShellSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite">
      <div className="border-b border-[var(--border)]">
        <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-6 py-3">
          <Skeleton className="h-6 w-56" />
          <Skeleton className="h-11 w-24" />
        </div>
      </div>
      <div className="mx-auto w-full max-w-5xl px-6 py-10">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="mt-6 h-40 w-full" />
      </div>
    </div>
  );
}
