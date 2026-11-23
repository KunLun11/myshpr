import { CheckCircle2, Clock, Circle, FilePenLine, Flag, PackageCheck, Square } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ProjectStatus } from "@/types/api";

type StatusMeta = {
  label: string;
  variant: "secondary" | "info" | "success" | "warning" | "danger";
  Icon: typeof Circle;
};

const STATUS_META: Record<ProjectStatus, StatusMeta> = {
  idea: { label: "Идея", variant: "secondary", Icon: Circle },
  topic_draft: { label: "Черновик темы", variant: "info", Icon: FilePenLine },
  topic_submitted: { label: "На проверке", variant: "warning", Icon: Clock },
  topic_approved: { label: "Тема утверждена", variant: "success", Icon: CheckCircle2 },
  product_draft: { label: "Выбор продукта", variant: "info", Icon: Square },
  product_defined: { label: "Продукт определён", variant: "success", Icon: PackageCheck },
  in_progress: { label: "Работа над проектом", variant: "info", Icon: Square },
  ready_for_defense: { label: "Готов к защите", variant: "warning", Icon: Flag },
  defended: { label: "Защищён", variant: "success", Icon: CheckCircle2 },
  archived: { label: "Архив", variant: "secondary", Icon: Circle },
};

export function projectStatusMeta(status: ProjectStatus): StatusMeta {
  return STATUS_META[status] ?? STATUS_META.idea;
}

/** Status is never communicated by colour alone: icon + text + tinted badge. */
export function ProjectStatusBadge({
  status,
  className,
}: {
  status: ProjectStatus;
  className?: string;
}) {
  const meta = projectStatusMeta(status);
  const Icon = meta.Icon;
  return (
    <Badge variant={meta.variant} className={className}>
      <Icon className="mr-1 size-3.5" aria-hidden="true" />
      {meta.label}
    </Badge>
  );
}
