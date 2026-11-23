"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";
import type { UserRole } from "@/types/api";

interface NavItem {
  href: string;
  label: string;
}

const ROOT_PATHS = new Set(["/cabinet", "/teacher", "/admin"]);

const NAV: Record<UserRole, NavItem[]> = {
  student: [
    { href: "/cabinet", label: "Проект" },
    { href: "/cabinet/topic", label: "Мастер темы" },
    { href: "/cabinet/product", label: "Продукт" },
    { href: "/cabinet/work", label: "Работа" },
  ],
  teacher: [
    { href: "/teacher", label: "Классы" },
    { href: "/teacher/projects", label: "Ученики" },
    { href: "/teacher/submissions", label: "Проверка тем" },
    { href: "/teacher/topics", label: "Реестр" },
  ],
  school_admin: [
    { href: "/admin", label: "Классы" },
    { href: "/admin/years", label: "Годы" },
    { href: "/admin/references", label: "Справочники" },
    { href: "/admin/checklist", label: "Чек-лист" },
    { href: "/admin/checkpoints", label: "Точки" },
    { href: "/admin/students", label: "Ученики" },
    { href: "/admin/audit", label: "Аудит" },
  ],
  super_admin: [
    { href: "/admin", label: "Классы" },
    { href: "/admin/schools", label: "Школы" },
    { href: "/admin/years", label: "Годы" },
    { href: "/admin/references", label: "Справочники" },
    { href: "/admin/checklist", label: "Чек-лист" },
    { href: "/admin/checkpoints", label: "Точки" },
    { href: "/admin/students", label: "Ученики" },
    { href: "/admin/audit", label: "Аудит" },
  ],
};

export function ShellNav({ role }: { role: UserRole }) {
  const pathname = usePathname();
  const items = NAV[role] ?? [];

  return (
    <nav
      aria-label="Основная навигация"
      className="-mx-1 flex max-w-full items-center gap-1 overflow-x-auto px-1 sm:overflow-visible"
    >
      {items.map((item) => {
        const active =
          pathname === item.href ||
          (!ROOT_PATHS.has(item.href) && pathname.startsWith(`${item.href}/`));
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "inline-flex min-h-11 shrink-0 items-center rounded-full px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]",
              active
                ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                : "text-[var(--muted-foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
