import Link from "next/link";
import type { ReactNode } from "react";

import { BrandMark } from "@/components/brand-mark";
import { LogoutButton } from "@/components/logout-button";
import { NotificationBell } from "@/components/notification-bell";
import { SessionKeeper } from "@/components/session-keeper";
import { ShellNav } from "@/components/shell-nav";
import { ThemeToggle } from "@/components/theme-toggle";
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
      <header className="sticky top-0 z-30 px-3 pt-3 sm:px-4">
        <div className="glass mx-auto flex w-full max-w-5xl flex-col gap-2 rounded-[var(--r-xl)] px-3 py-2.5 sm:px-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-2.5">
              <Link
                href={homeForRole(user.role)}
                className="flex min-w-0 items-center gap-2.5 rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              >
                <BrandMark className="size-9" />
                <span className="truncate font-display text-sm font-semibold tracking-tight sm:text-base">
                  <span className="sm:hidden">Проект</span>
                  <span className="hidden sm:inline">Индивидуальный проект</span>
                </span>
              </Link>
              <Badge variant="secondary" className="hidden shrink-0 md:inline-flex">
                {ROLE_LABELS[user.role]}
              </Badge>
            </div>
            <div className="flex items-center gap-2 lg:hidden">
              <ThemeToggle />
              <LogoutButton />
            </div>
          </div>
          <div className="flex min-w-0 items-center gap-1.5 sm:gap-2">
            <ShellNav role={user.role} />
            <div className="ml-1 flex items-center">
              <NotificationBell />
            </div>
            <span className="hidden max-w-[180px] truncate text-sm text-[var(--muted-foreground)] 2xl:inline">
              {user.full_name}
            </span>
            <div className="hidden lg:flex">
              <ThemeToggle />
            </div>
            <div className="hidden lg:block">
              <LogoutButton />
            </div>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8 sm:px-6 sm:py-10">
        <div className="animate-fade-up">{children}</div>
      </main>
    </div>
  );
}

export function AppShellSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite">
      <header className="px-3 pt-3 sm:px-4">
        <div className="glass mx-auto flex w-full max-w-5xl items-center justify-between rounded-[var(--r-xl)] px-4 py-3">
          <Skeleton className="h-9 w-64" />
          <Skeleton className="h-11 w-32 rounded-full" />
        </div>
      </header>
      <div className="mx-auto w-full max-w-5xl px-4 py-8 sm:px-6 sm:py-10">
        <Skeleton className="h-9 w-56" />
        <Skeleton className="mt-6 h-44 w-full rounded-[var(--r-lg)]" />
      </div>
    </div>
  );
}

