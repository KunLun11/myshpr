import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";

import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "relative inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full text-sm font-semibold transition-[transform,box-shadow,background-color,color] duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--background)] active:translate-y-0 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "bg-primary-gradient text-[var(--primary-foreground)] shadow-[var(--shadow-glow)] hover:-translate-y-0.5 hover:shadow-[var(--shadow-glow-strong)]",
        brand:
          "bg-[var(--brand)] text-[var(--brand-foreground)] shadow-[var(--shadow-soft)] hover:-translate-y-0.5 hover:brightness-105",
        outline:
          "glass border-[var(--glass-border)] text-[var(--foreground)] hover:-translate-y-0.5 hover:bg-[var(--glass-bg-strong)]",
        secondary:
          "bg-[var(--primary-soft)] text-[var(--primary)] hover:-translate-y-0.5 hover:brightness-95",
        ghost:
          "text-[var(--foreground)] hover:bg-[var(--muted)] hover:text-[var(--foreground)]",
        destructive:
          "bg-[var(--destructive)] text-[var(--destructive-foreground)] shadow-[var(--shadow-soft)] hover:-translate-y-0.5 hover:bg-[var(--destructive-hover)]",
      },
      size: {
        default: "h-11 px-5 py-2",
        sm: "h-11 rounded-full px-4",
        lg: "h-12 rounded-full px-8 text-base",
        icon: "h-11 w-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button ref={ref} className={cn(buttonVariants({ variant, size }), className)} {...props} />
  ),
);
Button.displayName = "Button";
