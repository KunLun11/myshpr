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
import type { AcademicYear, AdminCheckpoint, ProjectStatus } from "@/types/api";

const STATUSES: ProjectStatus[] = [
  "topic_draft",
  "topic_submitted",
  "topic_approved",
  "product_draft",
  "product_defined",
  "in_progress",
  "ready_for_defense",
  "defended",
];

const AUDIENCES = [
  { value: "student", label: "Ученики" },
  { value: "teacher", label: "Учителя" },
  { value: "both", label: "Все" },
] as const;

interface Draft {
  academic_year_id: string;
  code: string;
  title: string;
  description: string;
  due_at: string;
  required_status: ProjectStatus;
  audience: "student" | "teacher" | "both";
  sort_order: string;
  is_active: boolean;
}

const EMPTY: Draft = {
  academic_year_id: "",
  code: "",
  title: "",
  description: "",
  due_at: "",
  required_status: "topic_approved",
  audience: "student",
  sort_order: "100",
  is_active: true,
};

function toIso(value: string): string | null {
  if (!value) {
    return null;
  }
  return new Date(`${value}T00:00:00`).toISOString();
}

export function AdminCheckpoints({
  checkpoints,
  years,
}: {
  checkpoints: AdminCheckpoint[];
  years: AcademicYear[];
}) {
  const router = useRouter();
  const currentYear = years.find((year) => year.is_current)?.id ?? years[0]?.id ?? "";
  const [draft, setDraft] = useState<Draft>({ ...EMPTY, academic_year_id: currentYear });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<Draft>(EMPTY);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const yearNames = useMemo(() => new Map(years.map((year) => [year.id, year.name])), [years]);

  const update = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const updateEdit = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setEditDraft((current) => ({ ...current, [key]: value }));

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.post<AdminCheckpoint>("/admin/checkpoints", {
        academic_year_id: draft.academic_year_id,
        code: draft.code,
        title: draft.title,
        description: draft.description || null,
        due_at: toIso(draft.due_at),
        required_status: draft.required_status,
        audience: draft.audience,
        sort_order: Number(draft.sort_order) || 100,
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

  async function saveEdit(checkpointId: string) {
    setPending(true);
    setError(null);
    try {
      await api.patch<AdminCheckpoint>(`/admin/checkpoints/${checkpointId}`, {
        title: editDraft.title,
        description: editDraft.description || null,
        due_at: toIso(editDraft.due_at),
        required_status: editDraft.required_status,
        audience: editDraft.audience,
        sort_order: Number(editDraft.sort_order) || 100,
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

  async function toggleActive(item: AdminCheckpoint) {
    setPending(true);
    setError(null);
    try {
      await api.patch<AdminCheckpoint>(`/admin/checkpoints/${item.id}`, {
        is_active: !item.is_active,
      });
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
          <CardTitle>Новая контрольная точка</CardTitle>
          <CardDescription>
            Точки задают сроки: ученик видит ближайшую незакрытую точку в кабинете.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={create}>
            <Field label="Учебный год" htmlFor="cp-year">
              <select
                id="cp-year"
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
            <Field label="Код" htmlFor="cp-code">
              <input
                id="cp-code"
                className={inputClass}
                value={draft.code}
                onChange={(event) => update("code", event.target.value)}
                required
                maxLength={100}
              />
            </Field>
            <Field label="Название" htmlFor="cp-title">
              <input
                id="cp-title"
                className={inputClass}
                value={draft.title}
                onChange={(event) => update("title", event.target.value)}
                required
                maxLength={300}
              />
            </Field>
            <Field label="Срок" htmlFor="cp-due">
              <input
                id="cp-due"
                type="date"
                className={inputClass}
                value={draft.due_at}
                onChange={(event) => update("due_at", event.target.value)}
                required
              />
            </Field>
            <Field label="Описание" htmlFor="cp-description" className="md:col-span-2">
              <input
                id="cp-description"
                className={inputClass}
                value={draft.description}
                onChange={(event) => update("description", event.target.value)}
                maxLength={2000}
              />
            </Field>
            <Field label="Нужный статус" htmlFor="cp-status">
              <select
                id="cp-status"
                className={selectClass}
                value={draft.required_status}
                onChange={(event) =>
                  update("required_status", event.target.value as ProjectStatus)
                }
              >
                {STATUSES.map((status) => (
                  <option key={status} value={status}>
                    {STAGE_LABELS[status]}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Аудитория" htmlFor="cp-audience">
              <select
                id="cp-audience"
                className={selectClass}
                value={draft.audience}
                onChange={(event) =>
                  update("audience", event.target.value as Draft["audience"])
                }
              >
                {AUDIENCES.map((audience) => (
                  <option key={audience.value} value={audience.value}>
                    {audience.label}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Порядок" htmlFor="cp-sort">
              <input
                id="cp-sort"
                type="number"
                className={inputClass}
                value={draft.sort_order}
                onChange={(event) => update("sort_order", event.target.value)}
              />
            </Field>
            <CheckboxField
              id="cp-active"
              label="Активна"
              checked={draft.is_active}
              onChange={(value) => update("is_active", value)}
            />
            <div className="flex items-end">
              <Button
                type="submit"
                disabled={
                  pending ||
                  !draft.academic_year_id ||
                  !draft.due_at ||
                  draft.code.trim().length === 0 ||
                  draft.title.trim().length === 0
                }
              >
                {pending ? "Сохраняем…" : "Добавить точку"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Контрольные точки</CardTitle>
          <CardDescription>{checkpoints.length} записей</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[960px] text-left text-sm">
              <thead className="text-[var(--muted-foreground)]">
                <tr>
                  <th className="py-2 pr-4 font-medium">Год</th>
                  <th className="py-2 pr-4 font-medium">Точка</th>
                  <th className="py-2 pr-4 font-medium">Срок</th>
                  <th className="py-2 pr-4 font-medium">Нужный статус</th>
                  <th className="py-2 pr-4 font-medium">Аудитория</th>
                  <th className="py-2 pr-4 font-medium">Статус</th>
                  <th className="py-2 font-medium">Действия</th>
                </tr>
              </thead>
              <tbody>
                {checkpoints.map((item) =>
                  editingId === item.id ? (
                    <tr key={item.id} className="border-t border-[var(--border)] align-top">
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {yearNames.get(item.academic_year_id) ?? "—"}
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Название точки"
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
                      </td>
                      <td className="py-3 pr-4">
                        <select
                          aria-label="Нужный статус"
                          className={selectClass}
                          value={editDraft.required_status}
                          onChange={(event) =>
                            updateEdit("required_status", event.target.value as ProjectStatus)
                          }
                        >
                          {STATUSES.map((status) => (
                            <option key={status} value={status}>
                              {STAGE_LABELS[status]}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-3 pr-4">
                        <select
                          aria-label="Аудитория"
                          className={selectClass}
                          value={editDraft.audience}
                          onChange={(event) =>
                            updateEdit("audience", event.target.value as Draft["audience"])
                          }
                        >
                          {AUDIENCES.map((audience) => (
                            <option key={audience.value} value={audience.value}>
                              {audience.label}
                            </option>
                          ))}
                        </select>
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
                          id={`cp-edit-active-${item.id}`}
                          label="Активна"
                          checked={editDraft.is_active}
                          onChange={(value) => updateEdit("is_active", value)}
                        />
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button size="sm" disabled={pending} onClick={() => void saveEdit(item.id)}>
                            Сохранить
                          </Button>
                          <Button size="sm" variant="outline" onClick={() => setEditingId(null)}>
                            Отмена
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={item.id} className="border-t border-[var(--border)]">
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {yearNames.get(item.academic_year_id) ?? "—"}
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
                      <td className="py-3 pr-4">{stageLabel(item.required_status)}</td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {AUDIENCES.find((audience) => audience.value === item.audience)?.label ??
                          item.audience}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={item.is_active ? "success" : "secondary"}>
                          {item.is_active ? "Активна" : "Выключена"}
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
                                code: item.code,
                                title: item.title,
                                description: item.description ?? "",
                                due_at: item.due_at.slice(0, 10),
                                required_status: item.required_status,
                                audience: item.audience,
                                sort_order: String(item.sort_order),
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
