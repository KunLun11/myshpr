import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold leading-none transition-colors backdrop-blur-sm",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary-gradient text-[var(--primary-foreground)]",
        brand: "border-transparent bg-[var(--brand)] text-[var(--brand-foreground)]",
        secondary:
          "border-[var(--glass-border)] bg-[var(--secondary)] text-[var(--secondary-foreground)]",
        outline: "border-[var(--glass-border)] text-[var(--foreground)]",
        info: "border-transparent bg-[var(--info-soft)] text-[var(--info-soft-foreground)]",
        success: "border-transparent bg-[var(--success-soft)] text-[var(--success-soft-foreground)]",
        warning: "border-transparent bg-[var(--warning-soft)] text-[var(--warning-soft-foreground)]",
        danger:
          "border-transparent bg-[var(--destructive-soft)] text-[var(--destructive-soft-foreground)]",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { badgeVariants };
