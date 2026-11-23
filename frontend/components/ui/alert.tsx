import * as React from "react";

import { cn } from "@/lib/utils";

type AlertVariant = "error" | "info" | "success" | "warning";

const VARIANT_CLASSES: Record<AlertVariant, string> = {
  error:
    "border-[var(--destructive)]/25 bg-[var(--destructive-soft)] text-[var(--destructive-soft-foreground)]",
  info: "border-[var(--info)]/25 bg-[var(--info-soft)] text-[var(--info-soft-foreground)]",
  success:
    "border-[var(--success)]/25 bg-[var(--success-soft)] text-[var(--success-soft-foreground)]",
  warning:
    "border-[var(--warning)]/25 bg-[var(--warning-soft)] text-[var(--warning-soft-foreground)]",
};

export interface AlertProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: AlertVariant;
}

export function Alert({ className, variant = "error", ...props }: AlertProps) {
  return (
    <div
      role="alert"
      className={cn("rounded-[var(--radius-md)] border px-4 py-3 text-sm", VARIANT_CLASSES[variant], className)}
      {...props}
    />
  );
}
