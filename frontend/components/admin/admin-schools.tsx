"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useState } from "react";

import { CheckboxField, Field, inputClass } from "@/components/admin/form-controls";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import { authErrorMessage } from "@/lib/auth-errors";
import type { School } from "@/types/api";

interface Draft {
  name: string;
  city: string;
  region: string;
  timezone: string;
  is_active: boolean;
}

const EMPTY: Draft = {
  name: "",
  city: "",
  region: "",
  timezone: "Europe/Moscow",
  is_active: true,
};

function toDraft(school: School): Draft {
  return {
    name: school.name,
    city: school.city ?? "",
    region: school.region ?? "",
    timezone: school.timezone,
    is_active: school.is_active,
  };
}

export function AdminSchools({ schools }: { schools: School[] }) {
  const router = useRouter();
  const [draft, setDraft] = useState<Draft>(EMPTY);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDraft, setEditDraft] = useState<Draft>(EMPTY);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));
  const setEdit = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setEditDraft((current) => ({ ...current, [key]: value }));

  async function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await api.post<School>("/admin/schools", draft);
      setDraft(EMPTY);
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  function startEdit(school: School) {
    setEditingId(school.id);
    setEditDraft(toDraft(school));
    setError(null);
  }

  async function saveEdit(schoolId: string) {
    setPending(true);
    setError(null);
    try {
      await api.patch<School>(`/admin/schools/${schoolId}`, editDraft);
      setEditingId(null);
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
          <CardTitle>Новая школа</CardTitle>
          <CardDescription>Школа получает свой учебный год, классы и администратора.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={create}>
            <Field label="Название" htmlFor="school-name">
              <input
                id="school-name"
                className={inputClass}
                value={draft.name}
                onChange={(event) => set("name", event.target.value)}
                required
                maxLength={300}
              />
            </Field>
            <Field label="Город" htmlFor="school-city">
              <input
                id="school-city"
                className={inputClass}
                value={draft.city}
                onChange={(event) => set("city", event.target.value)}
                maxLength={200}
              />
            </Field>
            <Field label="Регион" htmlFor="school-region">
              <input
                id="school-region"
                className={inputClass}
                value={draft.region}
                onChange={(event) => set("region", event.target.value)}
                maxLength={200}
              />
            </Field>
            <Field label="Часовой пояс" htmlFor="school-timezone">
              <input
                id="school-timezone"
                className={inputClass}
                value={draft.timezone}
                onChange={(event) => set("timezone", event.target.value)}
                maxLength={100}
              />
            </Field>
            <CheckboxField
              id="school-active"
              label="Школа активна"
              checked={draft.is_active}
              onChange={(value) => set("is_active", value)}
            />
            <div className="flex items-end">
              <Button type="submit" disabled={pending || draft.name.trim().length === 0}>
                {pending ? "Сохраняем…" : "Создать школу"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Школы платформы</CardTitle>
          <CardDescription>{schools.length} записей</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-[var(--muted-foreground)]">
                <tr>
                  <th className="py-2 pr-4 font-medium">Название</th>
                  <th className="py-2 pr-4 font-medium">Город / регион</th>
                  <th className="py-2 pr-4 font-medium">Часовой пояс</th>
                  <th className="py-2 pr-4 font-medium">Статус</th>
                  <th className="py-2 font-medium">Действия</th>
                </tr>
              </thead>
              <tbody>
                {schools.map((school) =>
                  editingId === school.id ? (
                    <tr key={school.id} className="border-t border-[var(--border)] align-top">
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Название школы"
                          className={inputClass}
                          value={editDraft.name}
                          onChange={(event) => setEdit("name", event.target.value)}
                        />
                      </td>
                      <td className="py-3 pr-4">
                        <div className="space-y-2">
                          <input
                            aria-label="Город"
                            className={inputClass}
                            value={editDraft.city}
                            onChange={(event) => setEdit("city", event.target.value)}
                          />
                          <input
                            aria-label="Регион"
                            className={inputClass}
                            value={editDraft.region}
                            onChange={(event) => setEdit("region", event.target.value)}
                          />
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <input
                          aria-label="Часовой пояс"
                          className={inputClass}
                          value={editDraft.timezone}
                          onChange={(event) => setEdit("timezone", event.target.value)}
                        />
                        <div className="mt-1">
                          <CheckboxField
                            id={`school-active-${school.id}`}
                            label="Активна"
                            checked={editDraft.is_active}
                            onChange={(value) => setEdit("is_active", value)}
                          />
                        </div>
                      </td>
                      <td className="py-3 pr-4" />
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          <Button
                            size="sm"
                            disabled={pending}
                            onClick={() => void saveEdit(school.id)}
                          >
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
                    <tr key={school.id} className="border-t border-[var(--border)]">
                      <td className="py-3 pr-4 font-medium">{school.name}</td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                        {[school.city, school.region].filter(Boolean).join(", ") || "—"}
                      </td>
                      <td className="py-3 pr-4 text-[var(--muted-foreground)]">{school.timezone}</td>
                      <td className="py-3 pr-4">
                        <Badge variant={school.is_active ? "success" : "secondary"}>
                          {school.is_active ? "Активна" : "Отключена"}
                        </Badge>
                      </td>
                      <td className="py-3">
                        <Button size="sm" variant="outline" onClick={() => startEdit(school)}>
                          Изменить
                        </Button>
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
