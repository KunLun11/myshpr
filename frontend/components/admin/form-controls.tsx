"use client";

import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export const inputClass =
  "h-11 w-full rounded-[var(--r-md)] border border-[var(--input)] bg-[var(--input-bg)] px-3.5 text-sm text-[var(--foreground)] outline-none transition-[border-color,box-shadow] duration-200 placeholder:text-[var(--muted-foreground)] hover:border-[var(--ring)]/60 focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)] disabled:opacity-60";

export const selectClass = cn(inputClass, "pr-8");
export const textareaClass =
  "min-h-24 w-full rounded-[var(--r-md)] border border-[var(--input)] bg-[var(--input-bg)] px-3.5 py-2.5 text-sm text-[var(--foreground)] outline-none transition-[border-color,box-shadow] duration-200 placeholder:text-[var(--muted-foreground)] focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]";

interface FieldProps {
  label: string;
  htmlFor?: string;
  hint?: string;
  className?: string;
  children: ReactNode;
}

export function Field({ label, htmlFor, hint, className, children }: FieldProps) {
  return (
    <div className={cn("space-y-2", className)}>
      <label htmlFor={htmlFor} className="text-sm font-medium">
        {label}
      </label>
      {children}
      {hint ? <p className="text-xs text-[var(--muted-foreground)]">{hint}</p> : null}
    </div>
  );
}

interface CheckboxFieldProps {
  id: string;
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}

export function CheckboxField({ id, label, checked, onChange }: CheckboxFieldProps) {
  return (
    <label
      htmlFor={id}
      className="flex min-h-11 cursor-pointer items-center gap-3 text-sm font-medium"
    >
      <input
        id={id}
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="size-5 rounded border-[var(--input)] accent-[var(--primary)]"
      />
      {label}
    </label>
  );
}
