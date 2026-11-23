import { Check, Circle, CircleDot } from "lucide-react";

import { cn } from "@/lib/utils";

const STEPS = [
  { key: "idea", label: "Идея" },
  { key: "topic_draft", label: "Черновик темы" },
  { key: "topic_submitted", label: "На проверке" },
  { key: "topic_approved", label: "Тема утверждена" },
  { key: "product_draft", label: "Выбор продукта" },
  { key: "product_defined", label: "Продукт определён" },
  { key: "in_progress", label: "Работа" },
  { key: "ready_for_defense", label: "К защите" },
  { key: "defended", label: "Защищён" },
] as const;

const RANK = new Map<string, number>(STEPS.map((step, index) => [step.key, index]));

export function ProjectStepper({ current = "idea" }: { current?: string }) {
  const currentRank = RANK.get(current) ?? 0;

  return (
    <ol className="relative flex flex-col" aria-label="Этапы проекта">
      {STEPS.map((step, index) => {
        const done = index < currentRank;
        const active = index === currentRank;
        return (
          <li
            key={step.key}
            className="relative flex items-center gap-3 py-1.5"
            aria-current={active ? "step" : undefined}
          >
            {index < STEPS.length - 1 ? (
              <span
                aria-hidden="true"
                className={cn(
                  "absolute left-[0.9375rem] top-9 h-[calc(100%-1.25rem)] w-0.5 rounded-full",
                  done ? "bg-primary-gradient" : "bg-[var(--border)]",
                )}
              />
            ) : null}
            <span
              className={cn(
                "relative z-10 grid size-8 shrink-0 place-items-center rounded-full transition-transform duration-300",
                done && "bg-[var(--success-soft)] text-[var(--success-soft-foreground)]",
                active &&
                  "scale-110 bg-primary-gradient text-[var(--primary-foreground)] shadow-[var(--shadow-glow)]",
                !done &&
                  !active &&
                  "border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)]",
              )}
            >
              {done ? (
                <Check className="size-4" aria-hidden="true" />
              ) : active ? (
                <CircleDot className="size-4" aria-hidden="true" />
              ) : (
                <Circle className="size-3" aria-hidden="true" />
              )}
            </span>
            <span
              className={cn(
                "text-sm",
                active && "font-semibold text-[var(--foreground)]",
                done && "text-[var(--foreground)]",
                !done && !active && "text-[var(--muted-foreground)]",
              )}
            >
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
