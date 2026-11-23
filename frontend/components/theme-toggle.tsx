"use client";

import { Moon, Sun } from "lucide-react";

import { cn } from "@/lib/utils";

const STORAGE_KEY = "project-theme";

/**
 * Day/night switch. The icon is chosen with CSS from the `data-theme`
 * attribute, so the markup is identical on the server and the client and
 * there is no hydration flash.
 */
export function ThemeToggle({ className }: { className?: string }) {
  function toggle() {
    const root = document.documentElement;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private mode / storage disabled: the theme still applies for this session.
    }
  }

  return (
    <button
      type="button"
      onClick={toggle}
      className={cn("theme-toggle", className)}
      aria-label="Переключить дневную и ночную тему"
      title="День / ночь"
    >
      <Moon className="theme-icon theme-icon--moon size-[1.15rem]" aria-hidden="true" />
      <Sun className="theme-icon theme-icon--sun size-[1.15rem]" aria-hidden="true" />
    </button>
  );
}
