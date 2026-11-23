"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Info,
  LoaderCircle,
  ThumbsDown,
  ThumbsUp,
  X,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiError } from "@/lib/api";
import type { CheckLevel, Submission } from "@/types/api";

const DUPLICATE_LABELS: Record<CheckLevel, string> = {
  ok: "Повторов нет",
  warn: "Похожая тема",
  block: "Тема занята",
};

const BROADNESS_LABELS: Record<CheckLevel, string> = {
  ok: "Ширина в норме",
  warn: "Можно сузить",
  block: "Слишком широко",
};

function levelVariant(level: CheckLevel): "success" | "warning" | "danger" {
  return level === "ok" ? "success" : level === "warn" ? "warning" : "danger";
}

function LevelBadge({
  level,
  label,
}: {
  level: CheckLevel;
  label: string;
}) {
  const Icon = level === "ok" ? CheckCircle2 : level === "warn" ? AlertTriangle : X;
  return (
    <Badge variant={levelVariant(level)}>
      <Icon className="mr-1 size-3.5" aria-hidden="true" />
      {label}
    </Badge>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message;
  }
  return "Не удалось связаться с сервером. Попробуйте ещё раз.";
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
  });
}

export function ReviewQueue({ initialItems }: { initialItems: Submission[] }) {
  const [items, setItems] = useState(initialItems);

  function resolve(id: string) {
    setItems((current) => current.filter((item) => item.id !== id));
  }

  if (items.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <CheckCircle2 className="size-5 text-[var(--success)]" aria-hidden="true" />
            Очередь пуста
          </CardTitle>
          <CardDescription>
            Новые темы появятся здесь, как только ученики отправят их на проверку.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Link href="/teacher/topics" className={buttonVariants({ variant: "outline" })}>
            Открыть реестр тем
          </Link>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <ReviewCard key={item.id} item={item} onResolved={() => resolve(item.id)} />
      ))}
    </div>
  );
}

function ReviewCard({ item, onResolved }: { item: Submission; onResolved: () => void }) {
  const [mode, setMode] = useState<"approve" | "reject" | null>(null);
  const [comment, setComment] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsComment = item.duplicate_level !== "ok" || item.broadness_level !== "ok";

  async function decide(action: "approve" | "reject") {
    setPending(true);
    setError(null);
    try {
      await api.post<Submission>(`/teacher/submissions/${item.id}/${action}`, {
        comment: comment.trim() || null,
      });
      onResolved();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1">
            <CardTitle className="text-lg">{item.title}</CardTitle>
            <CardDescription>
              {item.student_full_name} · {item.class_label}
              {item.interest_area_name ? ` · ${item.interest_area_name}` : ""}
            </CardDescription>
          </div>
          <Badge variant="secondary">
            <Clock className="mr-1 size-3.5" aria-hidden="true" />
            отправлено {formatDate(item.submitted_at)}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
            Исследовательский вопрос
          </p>
          <p className="text-sm">{item.research_question}</p>
        </div>

        <div className="flex flex-wrap gap-2">
          <LevelBadge
            level={item.duplicate_level}
            label={`Повтор: ${DUPLICATE_LABELS[item.duplicate_level]}`}
          />
          <LevelBadge
            level={item.broadness_level}
            label={`Ширина: ${BROADNESS_LABELS[item.broadness_level]} · ${
              item.broadness_score ?? "—"
            }/100`}
          />
        </div>

        {item.duplicate_of_title ? (
          <p className="flex items-start gap-2 text-sm text-[var(--muted-foreground)]">
            <Info className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            Похожая тема: «{item.duplicate_of_title}»
          </p>
        ) : null}

        {item.broadness_reasons.length > 0 ? (
          <ul className="space-y-1 text-sm text-[var(--muted-foreground)]">
            {item.broadness_reasons.map((reason) => (
              <li key={reason} className="flex gap-2">
                <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                {reason}
              </li>
            ))}
          </ul>
        ) : null}

        {error ? <Alert>{error}</Alert> : null}

        {mode ? (
          <div className="space-y-3 rounded-[var(--radius-md)] bg-[var(--muted)] p-4">
            <label htmlFor={`comment-${item.id}`} className="text-sm font-medium">
              {mode === "approve"
                ? needsComment
                  ? "Комментарий обязателен: проверка нашла замечания"
                  : "Комментарий для ученика (необязательно)"
                : "Причина отклонения (обязательно)"}
            </label>
            <textarea
              id={`comment-${item.id}`}
              value={comment}
              onChange={(event) => setComment(event.target.value)}
              rows={3}
              maxLength={2000}
              placeholder={
                mode === "approve"
                  ? "Например: тема сужена по месту и группе, можно утверждать."
                  : "Например: уточните, какой участок реки вы исследуете."
              }
              className="w-full rounded-[var(--radius-md)] border border-[var(--input)] bg-[var(--background)] px-3 py-2 text-sm outline-none focus-visible:border-[var(--ring)] focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            />
            <div className="flex flex-wrap gap-2">
              <Button
                variant={mode === "approve" ? "default" : "destructive"}
                onClick={() => decide(mode)}
                disabled={
                  pending ||
                  (mode === "reject" && comment.trim().length < 3) ||
                  (mode === "approve" && needsComment && comment.trim().length < 3)
                }
              >
                {pending ? (
                  <LoaderCircle className="animate-spin" aria-hidden="true" />
                ) : mode === "approve" ? (
                  <ThumbsUp aria-hidden="true" />
                ) : (
                  <ThumbsDown aria-hidden="true" />
                )}
                {mode === "approve" ? "Утвердить тему" : "Отклонить тему"}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setMode(null);
                  setError(null);
                }}
                disabled={pending}
              >
                Отмена
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            <Button onClick={() => setMode("approve")}>
              <ThumbsUp aria-hidden="true" />
              Утвердить
            </Button>
            <Button variant="outline" onClick={() => setMode("reject")}>
              <ThumbsDown aria-hidden="true" />
              Отклонить
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
