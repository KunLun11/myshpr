import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "border-transparent bg-[var(--primary)] text-[var(--primary-foreground)]",
        brand: "border-transparent bg-[var(--brand)] text-[var(--brand-foreground)]",
        secondary: "border-transparent bg-[var(--muted)] text-[var(--muted-foreground)]",
        outline: "text-[var(--foreground)]",
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
