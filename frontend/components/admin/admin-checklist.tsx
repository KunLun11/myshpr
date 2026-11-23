"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useMemo, useState } from "react";

import { CheckboxField, Field, inputClass, selectClass } from "@/components/admin/form-controls";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { authErrorMessage } from "@/lib/auth-errors";
import { formatDate } from "@/lib/format";
import { STAGE_LABELS, stageLabel } from "@/lib/stages";
import type { AcademicYear, AdminChecklistItem, ProjectStatus } from "@/types/api";

const STAGES: ProjectStatus[] = [
  "topic_draft",
  "topic_submitted",
  "topic_approved",
  "product_draft",
  "product_defined",
  "in_progress",
  "ready_for_defense",
  "defended",
];

interface Draft {
  academic_year_id: string;
  stage: ProjectStatus;
  code: string;
  title: string;
  description: string;
  sort_order: string;
  is_required: boolean;
  due_at: string;
  is_active: boolean;
}

const EMPTY: Draft = {
  academic_year_id: "",
  stage: "in_progress",
  code: "",
  title: "",
  description: "",
  sort_order: "100",
  is_required: true,
  due_at: "",
  is_active: true,
};

function toIso(value: string): string | null {
  if (!value) {
    return null;
  }
  return new Date(`${value}T00:00:00`).toISOString();
}

function toDateInput(value: string | null): string {
  return value ? value.slice(0, 10) : "";
}

export function AdminChecklist({
  items,
  years,
}: {
  items: AdminChecklistItem[];
  years: AcademicYear[];
}) {
  const router = useRouter();
  const currentYear = years.find((year) => year.is_current)?.id ?? years[0]?.id ?? "";
  const [draft, setDraft] = useState<Draft>({ ...EMPTY, academic_year_id: currentYear });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<Draft>(EMPTY);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const yearNames = useMemo(
    () => new Map(years.map((year) => [year.id, year.name])),
    [years],
  );

  const update = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const updateEdit = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setEditDraft((current) => ({ ...current, [key]: value }));

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.post<AdminChecklistItem>("/admin/checklist-items", {
        academic_year_id: draft.academic_year_id,
        stage: draft.stage,
        code: draft.code,
        title: draft.title,
        description: draft.description || null,
        sort_order: Number(draft.sort_order) || 100,
        is_required: draft.is_required,
        due_at: toIso(draft.due_at),
        is_active: draft.is_active,
      });
      setDraft((current) => ({ ...current, code: "", title: "", description: "", due_at: "" }));
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  async function saveEdit(itemId: string) {
    setPending(true);
    setError(null);
    try {
      await api.patch<AdminChecklistItem>(`/admin/checklist-items/${itemId}`, {
        title: editDraft.title,
        description: editDraft.description || null,
        sort_order: Number(editDraft.sort_order) || 100,
        is_required: editDraft.is_required,
        due_at: toIso(editDraft.due_at),
        is_active: editDraft.is_active,
      });
      setEditingId(null);
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  async function toggleActive(item: AdminChecklistItem) {
    setPending(true);
    setError(null);
    try {
      await api.patch<AdminChecklistItem>(`/admin/checklist-items/${item.id}`, {
        is_active: !item.is_active,
      });
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  async function deactivate(item: AdminChecklistItem) {
    setPending(true);
    setError(null);
    try {
      await api.delete(`/admin/checklist-items/${item.id}`);
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-6">
      {error ? <Alert>{error}</Alert> : null}

      <Card>
        <CardHeader>
          <CardTitle>Новый пункт чек-листа</CardTitle>
          <CardDescription>
            Шаблон этапов. Пункты года действуют для всех классов школы.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={create}>
            <Field label="Учебный год" htmlFor="item-year">
              <select
                id="item-year"
                className={selectClass}
                value={draft.academic_year_id}
                onChange={(event) => update("academic_year_id", event.target.value)}
                required
              >
                <option value="" disabled>
                  Выберите год
                </option>
                {years.map((year) => (
                  <option key={year.id} value={year.id}>
                    {year.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Этап" htmlFor="item-stage">
              <select
                id="item-stage"
                className={selectClass}
                value={draft.stage}
                onChange={(event) => update("stage", event.target.value as ProjectStatus)}
              >
                {STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {STAGE_LABELS[stage]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Код" htmlFor="item-code" hint="уникален внутри года">
              <input
                id="item-code"
                className={inputClass}
                value={draft.code}
                onChange={(event) => update("code", event.target.value)}
                required
                maxLength={100}
              />
            </Field>
            <Field label="Название" htmlFor="item-title">
              <input
                id="item-title"
                className={inputClass}
                value={draft.title}
                onChange={(event) => update("title", event.target.value)}
                required
                maxLength={300}
              />
            </Field>
            <Field label="Описание" htmlFor="item-description" className="md:col-span-2">
              <input
                id="item-description"
                className={inputClass}
                value={draft.description}
                onChange={(event) => update("description", event.target.value)}
                maxLength={2000}
              />
            </Field>
            <Field label="Срок" htmlFor="item-due">
              <input
                id="item-due"
                type="date"
                className={inputClass}
                value={draft.due_at}
                onChange={(event) => update("due_at", event.target.value)}
              />
            </Field>
            <Field label="Порядок" htmlFor="item-sort">
              <input
                id="item-sort"
                type="number"
                className={inputClass}
                value={draft.sort_order}
                onChange={(event) => update("sort_order", event.target.value)}
              />
            </Field>
            <CheckboxField
              id="item-required"
              label="Обязательный"
              checked={draft.is_required}
              onChange={(value) => update("is_required", value)}
            />
            <CheckboxField
              id="item-active"
              label="Активен"
              checked={draft.is_active}
              onChange={(value) => update("is_active", value)}
            />
            <div className="flex items-end">
              <Button
                type="submit"
                disabled={
                  pending ||
                  !draft.academic_year_id ||
                  draft.code.trim().length === 0 ||
                  draft.title.trim().length === 0
                }
              >
                {pending ? "Сохраняем…" : "Добавить пункт"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Шаблон чек-листа</CardTitle>
          <CardDescription>{items.length} пунктов</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="text-[var(--muted-foreground)]">
                <tr>
                  <th className="py-2 pr-4 font-medium">Год / этап</th>
                  <th className="py-2 pr-4 font-medium">Пункт</th>
                  <th className="py-2 pr-4 font-medium">Срок</th>
                  <th className="py-2 pr-4 font-medium">Обязательный</th>
                  <th className="py-2 pr-4 font-medium">Статус</th>
                  <th className="py-2 font-medium">Действия</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) =>
                  editingId === item.id ? (
                    <tr key={item.id} className="border-t border-[var(--border)] align-top">
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {yearNames.get(item.academic_year_id) ?? "—"}
                        <div>{stageLabel(item.stage)}</div>
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Название пункта"
                          className={inputClass}
                          value={editDraft.title}
                          onChange={(event) => updateEdit("title", event.target.value)}
                        />
                        <input
                          aria-label="Описание"
                          className={`${inputClass} mt-2`}
                          value={editDraft.description}
                          onChange={(event) => updateEdit("description", event.target.value)}
                        />
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Срок"
                          type="date"
                          className={inputClass}
                          value={editDraft.due_at}
                          onChange={(event) => updateEdit("due_at", event.target.value)}
                        />
                        <input
                          aria-label="Порядок"
                          type="number"
                          className={`${inputClass} mt-2`}
                          value={editDraft.sort_order}
                          onChange={(event) => updateEdit("sort_order", event.target.value)}
                        />
                      </td>
                      <td className="py-3 pr-4">
                        <CheckboxField
                          id={`edit-required-${item.id}`}
                          label="Обязательный"
                          checked={editDraft.is_required}
                          onChange={(value) => updateEdit("is_required", value)}
                        />
                        <CheckboxField
                          id={`edit-active-${item.id}`}
                          label="Активен"
                          checked={editDraft.is_active}
                          onChange={(value) => updateEdit("is_active", value)}
                        />
                      </td>
                      <td className="py-3 pr-4" />
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button size="sm" disabled={pending} onClick={() => void saveEdit(item.id)}>
                            Сохранить
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditingId(null)}
                          >
                            Отмена
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={item.id} className="border-t border-[var(--border)]">
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        <div>{yearNames.get(item.academic_year_id) ?? "—"}</div>
                        <div>{stageLabel(item.stage)}</div>
                      </td>
                      <td className="py-3 pr-4">
                        <div className="font-medium">{item.title}</div>
                        <div className="font-mono text-xs text-[var(--muted-foreground)]">
                          {item.code}
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {formatDate(item.due_at)}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={item.is_required ? "info" : "secondary"}>
                          {item.is_required ? "Да" : "Нет"}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={item.is_active ? "success" : "secondary"}>
                          {item.is_active ? "Активен" : "Выключен"}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingId(item.id);
                              setEditDraft({
                                academic_year_id: item.academic_year_id,
                                stage: item.stage,
                                code: item.code,
                                title: item.title,
                                description: item.description ?? "",
                                sort_order: String(item.sort_order),
                                is_required: item.is_required,
                                due_at: toDateInput(item.due_at),
                                is_active: item.is_active,
                              });
                              setError(null);
                            }}
                          >
                            Изменить
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={pending}
                            onClick={() => void toggleActive(item)}
                          >
                            {item.is_active ? "Выключить" : "Включить"}
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={pending || !item.is_active}
                            onClick={() => void deactivate(item)}
                          >
                            Удалить
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
