"use client";

import { Check, Copy, KeyRound } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { authErrorMessage } from "@/lib/auth-errors";
import type { Invite } from "@/types/api";

export function InvitePanel({ classId }: { classId: string }) {
  const [invite, setInvite] = useState<Invite | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function createInvite() {
    setPending(true);
    setError(null);
    try {
      const created = await api.post<Invite>(`/admin/classes/${classId}/invites`, {
        expires_in_days: 14,
      });
      setInvite(created);
      setCopied(false);
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  async function copyCode() {
    if (!invite) {
      return;
    }
    try {
      await navigator.clipboard.writeText(invite.code);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="mt-4 space-y-3">
      {error ? <Alert>{error}</Alert> : null}

      {invite ? (
        <div className="rounded-[var(--radius-md)] bg-[var(--muted)] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-[var(--muted-foreground)]">
                Код для входа ученика
              </p>
              <code className="text-xl font-semibold tracking-[0.2em]">{invite.code}</code>
            </div>
            <Button variant="outline" size="sm" onClick={copyCode}>
              {copied ? <Check aria-hidden="true" /> : <Copy aria-hidden="true" />}
              {copied ? "Скопировано" : "Копировать"}
            </Button>
          </div>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">
            Действует до {new Date(invite.expires_at).toLocaleDateString("ru-RU")} · использовано{" "}
            {invite.uses_count}
            {invite.max_uses !== null ? ` из ${invite.max_uses}` : " · без ограничения"}
          </p>
        </div>
      ) : (
        <Button variant="outline" size="sm" onClick={createInvite} disabled={pending}>
          <KeyRound aria-hidden="true" />
          {pending ? "Создаём код…" : "Создать код приглашения"}
        </Button>
      )}
    </div>
  );
}
