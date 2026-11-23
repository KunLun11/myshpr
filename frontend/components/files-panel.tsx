"use client";

import {
  Archive,
  CheckCircle2,
  Download,
  File as FileIcon,
  FileText,
  Image as ImageIcon,
  LoaderCircle,
  Presentation,
  Trash2,
  UploadCloud,
} from "lucide-react";
import { useRef, useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError, uploadWithProgress } from "@/lib/api";
import { env } from "@/lib/env";
import { formatBytes, formatDateTime } from "@/lib/format";
import type { FileKind, ProjectFile } from "@/types/api";

const MAX_FILE_BYTES = 25 * 1024 * 1024;
const ACCEPT = ".pdf,.docx,.pptx,.png,.jpg,.jpeg,.zip";

const KIND_LABELS: Record<FileKind, string> = {
  research_draft: "Черновик исследования",
  final_work: "Итоговая работа",
  presentation: "Презентация",
  product_media: "Медиа продукта",
  other: "Другое",
};

function fileIcon(file: ProjectFile) {
  if (file.mime_type.startsWith("image/")) {
    return ImageIcon;
  }
  if (file.mime_type === "application/zip") {
    return Archive;
  }
  if (file.mime_type.includes("presentation")) {
    return Presentation;
  }
  if (file.mime_type === "application/pdf" || file.mime_type.includes("wordprocessing")) {
    return FileText;
  }
  return FileIcon;
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Не удалось загрузить файл. Проверьте соединение и попробуйте снова.";
}

export function FilesPanel({
  initialFiles,
  mode,
}: {
  initialFiles: ProjectFile[];
  mode: "student" | "teacher";
}) {
  const [files, setFiles] = useState(initialFiles);
  const [kind, setKind] = useState<FileKind>("final_work");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File | undefined) {
    if (!file) {
      return;
    }
    setError(null);
    if (file.size > MAX_FILE_BYTES) {
      setError("Файл больше 25 МБ. Выберите файл меньше.");
      return;
    }
    setUploading(true);
    setProgress(0);
    try {
      const uploaded = await uploadWithProgress<ProjectFile>(
        "/me/project/files",
        file,
        { kind },
        setProgress,
      );
      setFiles((current) => [uploaded, ...current]);
      setProgress(100);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setUploading(false);
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    }
  }

  async function handleDelete(file: ProjectFile) {
    setDeletingId(file.id);
    setError(null);
    try {
      await api.delete<void>(`/me/project/files/${file.id}`);
      setFiles((current) => current.filter((item) => item.id !== file.id));
      setConfirmId(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-4">
      {mode === "student" ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <UploadCloud className="size-5 text-[var(--primary)]" aria-hidden="true" />
              Загрузить файл
            </CardTitle>
            <CardDescription>
              PDF, DOCX, PPTX, PNG, JPEG или ZIP · до 25 МБ · не больше 10 файлов на проект.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-3">
              <label htmlFor="file-kind" className="text-sm font-medium">
                Тип файла
              </label>
              <select
                id="file-kind"
                value={kind}
                onChange={(event) => setKind(event.target.value as FileKind)}
                disabled={uploading}
                className="h-11 rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              >
                {Object.entries(KIND_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <Button
                type="button"
                variant="outline"
                onClick={() => inputRef.current?.click()}
                disabled={uploading}
              >
                {uploading ? (
                  <LoaderCircle className="animate-spin" aria-hidden="true" />
                ) : (
                  <UploadCloud aria-hidden="true" />
                )}
                Выбрать файл
              </Button>
              <input
                ref={inputRef}
                id="project-file"
                type="file"
                accept={ACCEPT}
                aria-label="Файл проекта"
                className="sr-only"
                onChange={(event) => handleFile(event.target.files?.[0])}
              />
            </div>

            {uploading ? (
              <div className="space-y-1">
                <div
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={progress}
                  aria-label="Загрузка файла"
                  className="h-2 w-full overflow-hidden rounded-full bg-[var(--muted)]"
                >
                  <div
                    className="h-full rounded-full bg-[var(--primary)] transition-[width]"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <p className="text-xs text-[var(--muted-foreground)]">Загрузка: {progress}%</p>
              </div>
            ) : null}

            {error ? <Alert>{error}</Alert> : null}
          </CardContent>
        </Card>
      ) : error ? (
        <Alert>{error}</Alert>
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-lg">Файлы проекта</CardTitle>
            <Badge variant="secondary">{files.length} файлов</Badge>
          </div>
          <CardDescription>
            Файлы доступны только ученику, его учителю и администрации школы.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {files.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <FileIcon className="size-8 text-[var(--muted-foreground)]" aria-hidden="true" />
              <p className="text-sm text-[var(--muted-foreground)]">
                Пока нет файлов. Добавьте черновик, презентацию или итоговую работу.
              </p>
            </div>
          ) : (
            <ul className="space-y-2">
              {files.map((file) => {
                const Icon = fileIcon(file);
                const available = file.status === "available";
                return (
                  <li
                    key={file.id}
                    className="flex flex-col gap-3 rounded-[var(--radius-md)] border border-[var(--border)] p-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <span className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-[var(--muted)] text-[var(--muted-foreground)]">
                        <Icon className="size-4" aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{file.original_name}</p>
                        <p className="text-xs text-[var(--muted-foreground)]">
                          {KIND_LABELS[file.kind]} · {formatBytes(file.size_bytes)} ·{" "}
                          {formatDateTime(file.created_at)}
                        </p>
                        {!available ? (
                          <Badge variant="warning" className="mt-1">
                            Проверяется
                          </Badge>
                        ) : null}
                      </div>
                    </div>

                    <div className="flex shrink-0 flex-wrap items-center gap-2">
                      {available ? (
                        <a
                          href={`${env.apiBase}${file.download_url}`}
                          className={buttonVariants({ variant: "outline", size: "sm" })}
                        >
                          <Download aria-hidden="true" />
                          Скачать
                        </a>
                      ) : null}
                      {mode === "student" ? (
                        confirmId === file.id ? (
                          <>
                            <span className="text-xs text-[var(--muted-foreground)]">
                              Удалить файл?
                            </span>
                            <Button
                              size="sm"
                              variant="destructive"
                              onClick={() => handleDelete(file)}
                              disabled={deletingId === file.id}
                            >
                              {deletingId === file.id ? (
                                <LoaderCircle className="animate-spin" aria-hidden="true" />
                              ) : (
                                <CheckCircle2 aria-hidden="true" />
                              )}
                              Да
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => setConfirmId(null)}
                              disabled={deletingId === file.id}
                            >
                              Нет
                            </Button>
                          </>
                        ) : (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setConfirmId(file.id)}
                          >
                            <Trash2 aria-hidden="true" />
                            Удалить
                          </Button>
                        )
                      ) : null}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
