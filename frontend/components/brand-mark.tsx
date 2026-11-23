import { Sparkles } from "lucide-react";

import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <span className={cn("brand-mark", className)} aria-hidden="true">
      <Sparkles className="size-[1.05rem]" />
    </span>
  );
}
