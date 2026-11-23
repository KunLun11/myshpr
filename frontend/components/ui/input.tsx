import * as React from "react";

import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, type = "text", ...props }, ref) => (
    <input
      ref={ref}
      type={type}
      className={cn(
        "flex h-11 w-full rounded-[var(--r-md)] border border-[var(--input)] bg-[var(--input-bg)] px-3.5 py-2 text-sm text-[var(--foreground)] outline-none transition-[border-color,box-shadow,background-color] duration-200 placeholder:text-[var(--muted-foreground)] hover:border-[var(--ring)]/60 focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
