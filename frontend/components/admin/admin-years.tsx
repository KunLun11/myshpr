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
import type { AcademicYear, School } from "@/types/api";

interface Draft {
  school_id: string;
  name: string;
  starts_on: string;
  ends_on: string;
  is_current: boolean;
}

export function AdminYears({
  years,
  schools,
  canPickSchool,
}: {
  years: AcademicYear[];
  schools: School[];
  canPickSchool: boolean;
}) {
  const router = useRouter();
  const defaultSchool = schools[0]?.id ?? "";
  const [draft, setDraft] = useState<Draft>({
    school_id: defaultSchool,
    name: "",
    starts_on: "",
    ends_on: "",
    is_current: false,
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState({ name: "", starts_on: "", ends_on: "" });
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const schoolNames = useMemo(
    () => new Map(schools.map((school) => [school.id, school.name])),
    [schools],
  );

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        name: draft.name,
        starts_on: draft.starts_on,
        ends_on: draft.ends_on,
        is_current: draft.is_current,
      };
      if (canPickSchool && draft.school_id) {
        body.school_id = draft.school_id;
      }
      await api.post<AcademicYear>("/admin/academic-years", body);
      setDraft((current) => ({
        ...current,
        name: "",
        starts_on: "",
        ends_on: "",
        is_current: false,
      }));
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  async function saveEdit(yearId: string) {
    setPending(true);
    setError(null);
    try {
      await api.patch<AcademicYear>(`/admin/academic-years/${yearId}`, editDraft);
      setEditingId(null);
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  async function makeCurrent(yearId: string) {
    setPending(true);
    setError(null);
    try {
      await api.patch<AcademicYear>(`/admin/academic-years/${yearId}`, { is_current: true });
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
          <CardTitle>Новый учебный год</CardTitle>
          <CardDescription>
            Текущий год используется при создании классов, чек-листов и контрольных точек.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2 xl:grid-cols-4" onSubmit={create}>
            {canPickSchool ? (
              <Field label="Школа" htmlFor="year-school">
                <select
                  id="year-school"
                  className={selectClass}
                  value={draft.school_id}
                  onChange={(event) => set("school_id", event.target.value)}
                  required
                >
                  {schools.map((school) => (
                    <option key={school.id} value={school.id}>
                      {school.name}
                    </option>
                  ))}
                </select>
              </Field>
            ) : null}
            <Field label="Название" htmlFor="year-name">
              <input
                id="year-name"
                className={inputClass}
                value={draft.name}
                onChange={(event) => set("name", event.target.value)}
                placeholder="2026/2027"
                required
                maxLength={100}
              />
            </Field>
            <Field label="Начало" htmlFor="year-start">
              <input
                id="year-start"
                type="date"
                className={inputClass}
                value={draft.starts_on}
                onChange={(event) => set("starts_on", event.target.value)}
                required
              />
            </Field>
            <Field label="Окончание" htmlFor="year-end">
              <input
                id="year-end"
                type="date"
                className={inputClass}
                value={draft.ends_on}
                onChange={(event) => set("ends_on", event.target.value)}
                required
              />
            </Field>
            <div className="flex items-end gap-4">
              <CheckboxField
                id="year-current"
                label="Сделать текущим"
                checked={draft.is_current}
                onChange={(value) => set("is_current", value)}
              />
              <Button
                type="submit"
                disabled={
                  pending || draft.name.trim().length === 0 || !draft.starts_on || !draft.ends_on
                }
              >
                {pending ? "Сохраняем…" : "Создать"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Учебные годы</CardTitle>
          <CardDescription>{years.length} записей</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <thead className="text-[var(--muted-foreground)]">
                <tr>
                  <th className="py-2 pr-4 font-medium">Год</th>
                  <th className="py-2 pr-4 font-medium">Школа</th>
                  <th className="py-2 pr-4 font-medium">Период</th>
                  <th className="py-2 pr-4 font-medium">Статус</th>
                  <th className="py-2 font-medium">Действия</th>
                </tr>
              </thead>
              <tbody>
                {years.map((year) =>
                  editingId === year.id ? (
                    <tr key={year.id} className="border-t border-[var(--border)] align-top">
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Название года"
                          className={inputClass}
                          value={editDraft.name}
                          onChange={(event) =>
                            setEditDraft((current) => ({ ...current, name: event.target.value }))
                          }
                        />
                      </td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {schoolNames.get(year.school_id) ?? "—"}
                      </td>
                      <td className="py-3 pr-4">
                        <div className="flex flex-col gap-2">
                          <input
                            aria-label="Начало года"
                            type="date"
                            className={inputClass}
                            value={editDraft.starts_on}
                            onChange={(event) =>
                              setEditDraft((current) => ({
                                ...current,
                                starts_on: event.target.value,
                              }))
                            }
                          />
                          <input
                            aria-label="Окончание года"
                            type="date"
                            className={inputClass}
                            value={editDraft.ends_on}
                            onChange={(event) =>
                              setEditDraft((current) => ({
                                ...current,
                                ends_on: event.target.value,
                              }))
                            }
                          />
                        </div>
                      </td>
                      <td className="py-3 pr-4" />
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button size="sm" disabled={pending} onClick={() => void saveEdit(year.id)}>
                            Сохранить
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={pending}
                            onClick={() => setEditingId(null)}
                          >
                            Отмена
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    <tr key={year.id} className="border-t border-[var(--border)]">
                      <td className="py-3 pr-4 font-medium">{year.name}</td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {schoolNames.get(year.school_id) ?? "—"}
                      </td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {formatDate(year.starts_on)} — {formatDate(year.ends_on)}
                      </td>
                      <td className="py-3 pr-4">
                        <Badge variant={year.is_current ? "success" : "secondary"}>
                          {year.is_current ? "Текущий" : "Архив"}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          {year.is_current ? null : (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={pending}
                              onClick={() => void makeCurrent(year.id)}
                            >
                              Сделать текущим
                            </Button>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingId(year.id);
                              setEditDraft({
                                name: year.name,
                                starts_on: year.starts_on,
                                ends_on: year.ends_on,
                              });
                              setError(null);
                            }}
                          >
                            Изменить
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
