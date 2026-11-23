"use client";

import {
  CheckCircle2,
  Eye,
  EyeOff,
  LoaderCircle,
  MessageSquare,
  Pencil,
  Send,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { STAGE_LABELS, stageLabel } from "@/lib/stages";
import type { CommentVisibility, TeacherComment } from "@/types/api";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Не удалось сохранить комментарий. Проверьте соединение.";
}

export function CommentsPanel({
  initialComments,
  mode,
  projectId,
}: {
  initialComments: TeacherComment[];
  mode: "student" | "teacher";
  projectId?: string;
}) {
  const [comments, setComments] = useState(initialComments);
  const [body, setBody] = useState("");
  const [visibility, setVisibility] = useState<CommentVisibility>("student_visible");
  const [stage, setStage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [savingEdit, setSavingEdit] = useState(false);
  const [confirmId, setConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleCreate() {
    if (!projectId || body.trim().length === 0) {
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await api.post<TeacherComment>(
        `/teacher/projects/${projectId}/comments`,
        {
          body: body.trim(),
          visibility,
          stage: stage || null,
        },
      );
      setComments((current) => [...current, created]);
      setBody("");
      setStage("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleEdit(comment: TeacherComment) {
    setSavingEdit(true);
    setError(null);
    try {
      const updated = await api.patch<TeacherComment>(
        `/teacher/comments/${comment.id}`,
        { body: editBody.trim() },
      );
      setComments((current) =>
        current.map((item) => (item.id === updated.id ? updated : item)),
      );
      setEditingId(null);
      setEditBody("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSavingEdit(false);
    }
  }

  async function handleDelete(comment: TeacherComment) {
    setDeletingId(comment.id);
    setError(null);
    try {
      await api.delete<void>(`/teacher/comments/${comment.id}`);
      setComments((current) => current.filter((item) => item.id !== comment.id));
      setConfirmId(null);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="space-y-4">
      {mode === "teacher" && projectId ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <MessageSquare className="size-5 text-[var(--primary)]" aria-hidden="true" />
              Новый комментарий
            </CardTitle>
            <CardDescription>
              Ученик прочитает комментарий, но не сможет ответить — это односторонняя
              обратная связь, а не чат.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <label htmlFor="comment-body" className="sr-only">
              Текст комментария
            </label>
            <textarea
              id="comment-body"
              value={body}
              onChange={(event) => setBody(event.target.value)}
              rows={4}
              maxLength={5000}
              className="w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
              placeholder="Например: добавьте два источника за последние три года и уточните методику."
            />
            <div className="flex flex-wrap items-end gap-3">
              <div className="space-y-1">
                <label htmlFor="comment-visibility" className="text-xs font-medium">
                  Кому видно
                </label>
                <select
                  id="comment-visibility"
                  value={visibility}
                  onChange={(event) =>
                    setVisibility(event.target.value as CommentVisibility)
                  }
                  className="h-11 rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                >
                  <option value="student_visible">Ученику</option>
                  <option value="teachers_only">Только учителям</option>
                </select>
              </div>
              <div className="space-y-1">
                <label htmlFor="comment-stage" className="text-xs font-medium">
                  Этап
                </label>
                <select
                  id="comment-stage"
                  value={stage}
                  onChange={(event) => setStage(event.target.value)}
                  className="h-11 rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                >
                  <option value="">Весь проект</option>
                  {Object.entries(STAGE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <Button
                onClick={handleCreate}
                disabled={submitting || body.trim().length === 0}
              >
                {submitting ? (
                  <LoaderCircle className="animate-spin" aria-hidden="true" />
                ) : (
                  <Send aria-hidden="true" />
                )}
                Отправить
              </Button>
            </div>
            {error ? <Alert>{error}</Alert> : null}
          </CardContent>
        </Card>
      ) : error ? (
        <Alert>{error}</Alert>
      ) : null}

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-lg">Комментарии учителя</CardTitle>
            <Badge variant="secondary">{comments.length}</Badge>
          </div>
          <CardDescription>
            {mode === "student"
              ? "Здесь появляются комментарии, которые учитель оставил для вас."
              : "Комментарии к проекту. «Только учителям» ученик не видит."}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {comments.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-8 text-center">
              <MessageSquare
                className="size-8 text-[var(--muted-foreground)]"
                aria-hidden="true"
              />
              <p className="text-sm text-[var(--muted-foreground)]">
                {mode === "student"
                  ? "Пока комментариев нет. Они появятся после проверки работы учителем."
                  : "Пока нет комментариев. Оставьте первый — он появится у ученика."}
              </p>
            </div>
          ) : (
            <ul className="space-y-3">
              {comments.map((comment) => (
                <li
                  key={comment.id}
                  className="rounded-[var(--radius-md)] border border-[var(--border)] p-4"
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="space-y-1">
                      <p className="text-sm font-medium">
                        {comment.author_full_name ?? "Учитель"}
                      </p>
                      <p className="text-xs text-[var(--muted-foreground)]">
                        {formatDateTime(comment.created_at)} · {stageLabel(comment.stage)}
                      </p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      {mode === "teacher" ? (
                        comment.visibility === "teachers_only" ? (
                          <Badge variant="warning">
                            <EyeOff className="mr-1 size-3" aria-hidden="true" />
                            Только учителям
                          </Badge>
                        ) : (
                          <Badge variant="success">
                            <Eye className="mr-1 size-3" aria-hidden="true" />
                            Видно ученику
                          </Badge>
                        )
                      ) : null}
                    </div>
                  </div>

                  {editingId === comment.id ? (
                    <div className="mt-3 space-y-2">
                      <label htmlFor={`edit-${comment.id}`} className="sr-only">
                        Изменить комментарий
                      </label>
                      <textarea
                        id={`edit-${comment.id}`}
                        value={editBody}
                        onChange={(event) => setEditBody(event.target.value)}
                        rows={3}
                        maxLength={5000}
                        className="w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
                      />
                      <div className="flex flex-wrap gap-2">
                        <Button
                          size="sm"
                          onClick={() => handleEdit(comment)}
                          disabled={savingEdit || editBody.trim().length === 0}
                        >
                          {savingEdit ? (
                            <LoaderCircle className="animate-spin" aria-hidden="true" />
                          ) : (
                            <CheckCircle2 aria-hidden="true" />
                          )}
                          Сохранить
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setEditingId(null);
                            setEditBody("");
                          }}
                          disabled={savingEdit}
                        >
                          <X aria-hidden="true" />
                          Отмена
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-2 whitespace-pre-wrap text-sm">{comment.body}</p>
                  )}

                  {mode === "teacher" && comment.can_edit && editingId !== comment.id ? (
                    <div className="mt-3 flex flex-wrap items-center gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          setEditingId(comment.id);
                          setEditBody(comment.body);
                        }}
                      >
                        <Pencil aria-hidden="true" />
                        Изменить
                      </Button>
                      {confirmId === comment.id ? (
                        <>
                          <span className="text-xs text-[var(--muted-foreground)]">
                            Удалить комментарий?
                          </span>
                          <Button
                            size="sm"
                            variant="destructive"
                            onClick={() => handleDelete(comment)}
                            disabled={deletingId === comment.id}
                          >
                            {deletingId === comment.id ? (
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
                            disabled={deletingId === comment.id}
                          >
                            Нет
                          </Button>
                        </>
                      ) : (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirmId(comment.id)}
                        >
                          <Trash2 aria-hidden="true" />
                          Удалить
                        </Button>
                      )}
                    </div>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
