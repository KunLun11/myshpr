"use client";

import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";

import { Field, inputClass, selectClass } from "@/components/admin/form-controls";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { uploadWithProgress } from "@/lib/api";
import { authErrorMessage } from "@/lib/auth-errors";
import { className as classLabel, formatDate } from "@/lib/format";
import type { AdminStudent, ClassSummary, StudentImportResult } from "@/types/api";

function credentialsCsv(result: StudentImportResult): string {
  const header = "full_name,email,temp_password";
  const rows = result.created.map((student) =>
    [student.full_name, student.email, student.temp_password]
      .map((value) => `"${value.replaceAll('"', '""')}"`)
      .join(","),
  );
  return [header, ...rows].join("\n");
}

export function AdminStudents({
  students,
  classes,
}: {
  students: AdminStudent[];
  classes: ClassSummary[];
}) {
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [classFilter, setClassFilter] = useState("");
  const [importClass, setImportClass] = useState(classes[0]?.id ?? "");
  const [pending, setPending] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StudentImportResult | null>(null);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return students.filter((student) => {
      if (classFilter && student.class_id !== classFilter) {
        return false;
      }
      if (!needle) {
        return true;
      }
      return (
        student.full_name.toLowerCase().includes(needle) ||
        student.email.toLowerCase().includes(needle)
      );
    });
  }, [students, query, classFilter]);

  async function upload() {
    const file = fileRef.current?.files?.[0];
    if (!file || !importClass) {
      return;
    }
    setPending(true);
    setError(null);
    setResult(null);
    setProgress(0);
    try {
      const payload = await uploadWithProgress<StudentImportResult>(
        `/admin/students/import?class_id=${importClass}`,
        file,
        {},
        setProgress,
      );
      setResult(payload);
      if (fileRef.current) {
        fileRef.current.value = "";
      }
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  function downloadCredentials() {
    if (!result) {
      return;
    }
    const blob = new Blob([credentialsCsv(result)], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "student-credentials.csv";
    link.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      {error ? <Alert>{error}</Alert> : null}

      <Card>
        <CardHeader>
          <CardTitle>Импорт учеников из CSV</CardTitle>
          <CardDescription>
            Колонки <code>full_name</code> и <code>email</code>. Ученики получают временный пароль
            и должны сменить его при первом входе.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Класс" htmlFor="import-class">
              <select
                id="import-class"
                className={selectClass}
                value={importClass}
                onChange={(event) => setImportClass(event.target.value)}
              >
                {classes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {classLabel(item)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Файл CSV" htmlFor="import-file">
              <input
                id="import-file"
                ref={fileRef}
                type="file"
                accept=".csv,text/csv"
                className="block min-h-11 w-full cursor-pointer rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 py-2.5 text-sm file:mr-3 file:rounded-[var(--radius-sm)] file:border-0 file:bg-[var(--muted)] file:px-3 file:py-1.5 file:text-sm"
              />
            </Field>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <Button
              type="button"
              disabled={pending || !importClass}
              onClick={() => void upload()}
            >
              {pending ? `Загружаем… ${progress}%` : "Импортировать"}
            </Button>
            <p className="text-sm text-[var(--muted-foreground)]">
              До 500 строк, не больше 1 МБ. Существующие email пропускаются.
            </p>
          </div>
          {pending ? (
            <div className="h-2 w-full overflow-hidden rounded-full bg-[var(--muted)]">
              <div
                className="h-full bg-[var(--primary)] transition-[width] duration-200 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          ) : null}
          {result ? (
            <div className="space-y-3">
              <Alert variant="success">
                Создано: {result.created_count}. Пропущено: {result.skipped_count}.
              </Alert>
              {result.created.length > 0 ? (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium">Временные пароли</p>
                    <Button type="button" size="sm" variant="outline" onClick={downloadCredentials}>
                      Скачать CSV
                    </Button>
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full min-w-[560px] text-left text-sm">
                      <thead className="text-[var(--muted-foreground)]">
                        <tr>
                          <th className="py-2 pr-4 font-medium">Ученик</th>
                          <th className="py-2 pr-4 font-medium">Email</th>
                          <th className="py-2 font-medium">Пароль</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.created.map((student) => (
                          <tr key={student.user_id} className="border-t border-[var(--border)]">
                            <td className="py-2 pr-4">{student.full_name}</td>
                            <td className="py-2 pr-4 text-[var(--muted-foreground)]">
                              {student.email}
                            </td>
                            <td className="py-2 font-mono text-xs">{student.temp_password}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <p className="text-xs text-[var(--muted-foreground)]">
                    Передайте пароли ученикам лично. После закрытия страницы они больше не
                    показываются.
                  </p>
                </div>
              ) : null}
              {result.skipped.length > 0 ? (
                <details className="rounded-[var(--radius-md)] border border-[var(--border)] p-3">
                  <summary className="cursor-pointer text-sm font-medium">
                    Пропущенные строки ({result.skipped.length})
                  </summary>
                  <ul className="mt-2 space-y-1 text-sm text-[var(--muted-foreground)]">
                    {result.skipped.map((row) => (
                      <li key={`${row.row}-${row.email ?? ""}`}>
                        Строка {row.row}: {row.reason}
                        {row.email ? ` (${row.email})` : ""}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ученики</CardTitle>
          <CardDescription>{filtered.length} из {students.length}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Поиск" htmlFor="student-search">
              <input
                id="student-search"
                className={inputClass}
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="ФИО или email"
              />
            </Field>
            <Field label="Класс" htmlFor="student-class">
              <select
                id="student-class"
                className={selectClass}
                value={classFilter}
                onChange={(event) => setClassFilter(event.target.value)}
              >
                <option value="">Все классы</option>
                {classes.map((item) => (
                  <option key={item.id} value={item.id}>
                    {classLabel(item)}
                  </option>
                ))}
              </select>
            </Field>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="text-[var(--muted-foreground)]">
                <tr>
                  <th className="py-2 pr-4 font-medium">ФИО</th>
                  <th className="py-2 pr-4 font-medium">Email</th>
                  <th className="py-2 pr-4 font-medium">Класс</th>
                  <th className="py-2 pr-4 font-medium">Год</th>
                  <th className="py-2 pr-4 font-medium">Статус</th>
                  <th className="py-2 font-medium">Добавлен</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((student) => (
                  <tr key={student.user_id} className="border-t border-[var(--border)]">
                    <td className="py-3 pr-4 font-medium">{student.full_name}</td>
                    <td className="py-3 pr-4 text-[var(--muted-foreground)]">{student.email}</td>
                    <td className="py-3 pr-4">
                      {student.class_label.startsWith(String(student.class_grade))
                        ? student.class_label
                        : `${student.class_grade}${student.class_label}`}
                    </td>
                    <td className="py-3 pr-4 text-[var(--muted-foreground)]">
                      {student.academic_year_name ?? "—"}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge variant={student.is_active ? "success" : "secondary"}>
                        {student.is_active ? "Активен" : "Отключён"}
                      </Badge>
                    </td>
                    <td className="py-3 text-[var(--muted-foreground)]">
                      {formatDate(student.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {filtered.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">
              Ничего не найдено. Измените фильтр или импортируйте учеников.
            </p>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}
