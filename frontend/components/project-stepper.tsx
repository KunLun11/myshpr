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
    <ol className="flex flex-col gap-2" aria-label="Этапы проекта">
      {STEPS.map((step, index) => {
        const done = index < currentRank;
        const active = index === currentRank;
        return (
          <li
            key={step.key}
            className={cn(
              "flex items-center gap-3 text-sm",
              active && "font-semibold text-[var(--foreground)]",
              !active && !done && "text-[var(--muted-foreground)]",
            )}
            aria-current={active ? "step" : undefined}
          >
            {done ? (
              <Check className="size-4 text-[var(--primary)]" aria-hidden="true" />
            ) : active ? (
              <CircleDot className="size-4 text-[var(--primary)]" aria-hidden="true" />
            ) : (
              <Circle className="size-4" aria-hidden="true" />
            )}
            <span>{step.label}</span>
          </li>
        );
      })}
    </ol>
  );
}
