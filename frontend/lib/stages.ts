import type { ProjectStatus } from "@/types/api";

export const STAGE_LABELS: Record<ProjectStatus, string> = {
  idea: "Идея",
  topic_draft: "Черновик темы",
  topic_submitted: "Тема на проверке",
  topic_approved: "Тема утверждена",
  product_draft: "Выбор продукта",
  product_defined: "Продукт определён",
  in_progress: "Работа над проектом",
  ready_for_defense: "Подготовка к защите",
  defended: "Защита",
  archived: "Архив",
};

export function stageLabel(status: ProjectStatus | string | null | undefined): string {
  if (!status) {
    return "Весь проект";
  }
  return STAGE_LABELS[status as ProjectStatus] ?? status;
}
