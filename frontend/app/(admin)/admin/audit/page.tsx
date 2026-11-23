import type { Metadata } from "next";
import { Suspense } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { requireUser } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";
import { serverApiGet } from "@/lib/server-api";
import type { AuditEntry } from "@/types/api";

export const metadata: Metadata = { title: "Журнал действий" };
export const instant = false;

const ACTION_LABELS: Record<string, string> = {
  "school.created": "Создана школа",
  "school.updated": "Изменена школа",
  "academic_year.created": "Создан учебный год",
  "academic_year.updated": "Изменён учебный год",
  "class.created": "Создан класс",
  "class.invite_created": "Создан код приглашения",
  "class.invite_revoked": "Отозван код приглашения",
  "checklist_item.created": "Добавлен пункт чек-листа",
  "checklist_item.updated": "Изменён пункт чек-листа",
  "checklist_item.deactivated": "Отключён пункт чек-листа",
  "checkpoint.created": "Создана контрольная точка",
  "checkpoint.updated": "Изменена контрольная точка",
  "interest_area.created": "Добавлена сфера интересов",
  "interest_area.updated": "Изменена сфера интересов",
  "product_category.created": "Добавлена категория продукта",
  "product_category.updated": "Изменена категория продукта",
  "students.imported": "Импорт учеников",
};

export default function AdminAuditPage() {
  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Журнал действий</h1>
        <p className="max-w-[70ch] text-[var(--muted-foreground)]">
          Последние 100 действий администраторов. Журнал только для чтения.
        </p>
      </header>
      <Suspense fallback={<AuditSkeleton />}>
        <AuditSection />
      </Suspense>
    </div>
  );
}

async function AuditSection() {
  await requireUser();
  const entries = await serverApiGet<AuditEntry[]>("/admin/audit-log?limit=100");
  if (entries === null) {
    return <Alert>Не удалось загрузить журнал. Обновите страницу.</Alert>;
  }
  if (entries.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Пока пусто</CardTitle>
          <CardDescription>Действия администраторов появятся здесь автоматически.</CardDescription>
        </CardHeader>
        <CardContent />
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Записи</CardTitle>
        <CardDescription>{entries.length} последних действий</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[820px] text-left text-sm">
            <thead className="text-[var(--muted-foreground)]">
              <tr>
                <th className="py-2 pr-4 font-medium">Когда</th>
                <th className="py-2 pr-4 font-medium">Кто</th>
                <th className="py-2 pr-4 font-medium">Действие</th>
                <th className="py-2 pr-4 font-medium">Объект</th>
                <th className="py-2 font-medium">Детали</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-t border-[var(--border)] align-top">
                  <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                    {formatDateTime(entry.created_at)}
                  </td>
                  <td className="py-3 pr-4">{entry.actor_name ?? "—"}</td>
                  <td className="py-3 pr-4">
                    <div className="font-medium">{ACTION_LABELS[entry.action] ?? entry.action}</div>
                    <div className="font-mono text-xs text-[var(--muted-foreground)]">
                      {entry.action}
                    </div>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge variant="secondary">{entry.entity_type}</Badge>
                    {entry.entity_id ? (
                      <div className="mt-1 max-w-[160px] truncate font-mono text-xs text-[var(--muted-foreground)]">
                        {entry.entity_id}
                      </div>
                    ) : null}
                  </td>
                  <td className="py-3 text-[var(--muted-foreground)]">
                    {entry.payload ? (
                      <code className="break-all text-xs">{JSON.stringify(entry.payload)}</code>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-4 text-xs text-[var(--muted-foreground)]">
          Показаны последние 100 записей вашей школы. Пароли и другие секреты в журнал не
          записываются.
        </p>
      </CardContent>
    </Card>
  );
}

function AuditSkeleton() {
  return (
    <div aria-busy="true" aria-live="polite">
      <Skeleton className="h-96 w-full" />
    </div>
  );
}
