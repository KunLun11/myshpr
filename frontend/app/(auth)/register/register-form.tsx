"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { FormEvent } from "react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { authErrorMessage } from "@/lib/auth-errors";
import { registerStudentRequest } from "@/lib/auth-client";

export function RegisterForm() {
  const router = useRouter();
  const params = useSearchParams();

  const [inviteCode, setInviteCode] = useState(params.get("code") ?? "");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await registerStudentRequest({
        invite_code: inviteCode.trim(),
        email: email.trim(),
        password,
        full_name: fullName.trim(),
      });
      router.replace("/cabinet");
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <Card className="w-full shadow-[var(--shadow-soft)]">
      <CardHeader>
        <CardTitle className="text-2xl">Регистрация ученика</CardTitle>
        <CardDescription>
          Понадобится код класса. Его выдаёт учитель или администратор школы.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="invite-code">Код класса</Label>
            <Input
              id="invite-code"
              value={inviteCode}
              onChange={(event) => setInviteCode(event.target.value.toUpperCase())}
              placeholder="Например, DEMO2026"
              autoComplete="one-time-code"
              className="font-mono tracking-[0.15em] uppercase"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="full-name">ФИО</Label>
            <Input
              id="full-name"
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              autoComplete="name"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="new-password"
              minLength={8}
              required
            />
            <p className="text-xs text-[var(--muted-foreground)]">Не короче 8 символов.</p>
          </div>

          {error ? <Alert>{error}</Alert> : null}

          <Button type="submit" className="w-full" disabled={pending}>
            {pending ? "Создаём аккаунт…" : "Зарегистрироваться"}
          </Button>
        </form>

        <p className="mt-6 text-sm text-[var(--muted-foreground)]">
          Уже есть аккаунт?{" "}
          <Link href="/login" className="font-medium text-[var(--primary)]">
            Войти
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
