"use client";

import { useRouter } from "next/navigation";
import type { FormEvent } from "react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import { authErrorMessage } from "@/lib/auth-errors";
import type { ClassSummary } from "@/types/api";

const SELECT_CLASSES =
  "h-11 w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]";

interface CreateClassFormProps {
  schools?: { id: string; name: string }[];
  canPickSchool?: boolean;
}

export function CreateClassForm({ schools = [], canPickSchool = false }: CreateClassFormProps) {
  const router = useRouter();
  const [schoolId, setSchoolId] = useState(schools[0]?.id ?? "");
  const [grade, setGrade] = useState("9");
  const [label, setLabel] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const query = canPickSchool && schoolId ? `?school_id=${schoolId}` : "";
      await api.post<ClassSummary>(`/admin/classes${query}`, {
        grade: Number(grade),
        label: label.trim(),
      });
      setLabel("");
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Новый класс</CardTitle>
        <CardDescription>Класс создаётся в текущем учебном году школы.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4 sm:flex-row sm:items-end" onSubmit={handleSubmit}>
          {canPickSchool ? (
            <div className="space-y-2 sm:w-56">
              <Label htmlFor="class-school">Школа</Label>
              <select
                id="class-school"
                className={SELECT_CLASSES}
                value={schoolId}
                onChange={(event) => setSchoolId(event.target.value)}
                required
              >
                {schools.map((school) => (
                  <option key={school.id} value={school.id}>
                    {school.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}
          <div className="space-y-2 sm:w-28">
            <Label htmlFor="grade">Параллель</Label>
            <select
              id="grade"
              className={SELECT_CLASSES}
              value={grade}
              onChange={(event) => setGrade(event.target.value)}
            >
              <option value="9">9</option>
              <option value="10">10</option>
              <option value="11">11</option>
            </select>
          </div>
          <div className="flex-1 space-y-2">
            <Label htmlFor="label">Литера</Label>
            <Input
              id="label"
              value={label}
              onChange={(event) => setLabel(event.target.value)}
              placeholder="А"
              maxLength={20}
              required
            />
          </div>
          <Button
            type="submit"
            disabled={
              pending ||
              label.trim().length === 0 ||
              (canPickSchool && (schools.length === 0 || !schoolId))
            }
          >
            {pending ? "Создаём…" : "Создать класс"}
          </Button>
        </form>
        {error ? <Alert className="mt-4">{error}</Alert> : null}
      </CardContent>
    </Card>
  );
}
