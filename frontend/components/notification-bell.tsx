"use client";

import {
  Bell,
  CalendarClock,
  Check,
  CheckCircle2,
  ClipboardCheck,
  Clock,
  ListChecks,
  MessageSquare,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { NotificationItem, NotificationList, NotificationType } from "@/types/api";

const TYPE_META: Record<NotificationType, { label: string; Icon: typeof Bell }> = {
  topic_decision: { label: "Решение по теме", Icon: CheckCircle2 },
  topic_review: { label: "Тема на проверке", Icon: ClipboardCheck },
  checkpoint_due: { label: "Контрольная точка", Icon: CalendarClock },
  inactivity: { label: "Активность", Icon: Clock },
  teacher_digest: { label: "Сводка по классу", Icon: Users },
  new_comment: { label: "Комментарий учителя", Icon: MessageSquare },
  checklist_due: { label: "Чек-лист", Icon: ListChecks },
};

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<NotificationList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await api.get<NotificationList>("/me/notifications?limit=20");
      setData(next);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Не удалось загрузить уведомления.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Defer so the first fetch does not synchronously update state in the effect.
    const handle = setTimeout(() => {
      void load();
    }, 0);
    return () => clearTimeout(handle);
  }, [load]);

  useEffect(() => {
    if (!open) {
      return;
    }
    function onPointerDown(event: MouseEvent) {
      if (
        containerRef.current !== null &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  async function markRead(notification: NotificationItem) {
    if (notification.is_read) {
      return;
    }
    try {
      await api.post(`/me/notifications/${notification.id}/read`);
      setData((current) =>
        current === null
          ? current
          : {
              ...current,
              unread_count: Math.max(current.unread_count - 1, 0),
              items: current.items.map((item) =>
                item.id === notification.id
                  ? { ...item, is_read: true, read_at: new Date().toISOString() }
                  : item,
              ),
            },
      );
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Не удалось отметить уведомление.",
      );
    }
  }

  const unread = data?.unread_count ?? 0;

  return (
    <div ref={containerRef} className="relative shrink-0">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label={
          unread > 0 ? `Уведомления, непрочитанных: ${unread}` : "Уведомления"
        }
        aria-expanded={open}
        aria-haspopup="dialog"
        onClick={() => setOpen((value) => !value)}
        className="relative"
      >
        <Bell aria-hidden="true" />
        {unread > 0 ? (
          <span className="absolute right-1.5 top-1.5 flex min-w-4 items-center justify-center rounded-full bg-[var(--destructive)] px-1 text-[10px] font-semibold leading-4 text-[var(--destructive-foreground)]">
            {unread > 9 ? "9+" : unread}
          </span>
        ) : null}
      </Button>

      {open ? (
        <div
          role="dialog"
          aria-label="Уведомления"
          className="absolute right-0 top-[calc(100%+0.5rem)] z-30 max-h-[70vh] w-[min(24rem,calc(100vw-2rem))] overflow-y-auto rounded-[var(--radius)] border border-[var(--border)] bg-[var(--popover)] p-4 text-[var(--popover-foreground)] shadow-[var(--shadow-popover)]"
        >
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-sm font-semibold">Уведомления</h2>
            {unread > 0 ? <Badge variant="danger">{unread} новых</Badge> : null}
          </div>

          {loading && data === null ? (
            <div className="mt-4 space-y-2" aria-busy="true" aria-live="polite">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : null}

          {error ? (
            <p role="alert" className="mt-4 text-sm text-[var(--destructive)]">
              {error}
            </p>
          ) : null}

          {!loading && data !== null && data.items.length === 0 ? (
            <p className="mt-4 text-sm text-[var(--muted-foreground)]">
              Пока нет уведомлений. Здесь появятся решения по теме, дедлайны и
              комментарии учителя.
            </p>
          ) : null}

          {data !== null && data.items.length > 0 ? (
            <ul className="mt-3 space-y-1">
              {data.items.map((notification) => {
                const meta = TYPE_META[notification.type] ?? TYPE_META.inactivity;
                const Icon = meta.Icon;
                return (
                  <li
                    key={notification.id}
                    className={cn(
                      "flex items-start gap-2 rounded-[var(--radius-md)] p-2.5",
                      notification.is_read
                        ? "bg-transparent"
                        : "bg-[var(--info-soft)]/60",
                    )}
                  >
                    <Icon
                      className="mt-0.5 size-4 shrink-0 text-[var(--primary)]"
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium">
                        {notification.is_read ? (
                          <span className="sr-only">Прочитано: </span>
                        ) : null}
                        {notification.title}
                      </p>
                      <p className="mt-0.5 text-xs text-[var(--muted-foreground)]">
                        {notification.body}
                      </p>
                      <p className="mt-1 text-[11px] text-[var(--muted-foreground)]">
                        {meta.label} · {formatDateTime(notification.created_at)}
                      </p>
                    </div>
                    {notification.is_read ? (
                      <Check
                        className="mt-1 size-4 shrink-0 text-[var(--success)]"
                        aria-label="Прочитано"
                      />
                    ) : (
                      <Button
                        type="button"
                        size="icon"
                        variant="ghost"
                        aria-label="Отметить прочитанным"
                        onClick={() => void markRead(notification)}
                      >
                        <Check aria-hidden="true" />
                      </Button>
                    )}
                  </li>
                );
              })}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
