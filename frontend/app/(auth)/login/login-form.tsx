"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import type { FormEvent } from "react";
import { useState } from "react";

import { SessionResume } from "@/components/session-resume";
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
import { loginRequest } from "@/lib/auth-client";
import { homeForRole } from "@/lib/roles";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      const user = await loginRequest(email.trim(), password);
      router.replace(next && next.startsWith("/") ? next : homeForRole(user.role));
      router.refresh();
    } catch (err) {
      setError(authErrorMessage(err));
    } finally {
      setPending(false);
    }
  }

  return (
    <Card className="w-full shadow-[var(--shadow-soft)]">
      {next ? <SessionResume next={next} /> : null}
      <CardHeader>
        <CardTitle className="text-2xl">Вход</CardTitle>
        <CardDescription>Войдите, чтобы продолжить работу над проектом.</CardDescription>
      </CardHeader>
      <CardContent>
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Пароль</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>

          {error ? <Alert>{error}</Alert> : null}

          <Button type="submit" className="w-full" disabled={pending}>
            {pending ? "Входим…" : "Войти"}
          </Button>
        </form>

        <p className="mt-6 text-sm text-[var(--muted-foreground)]">
          Нет аккаунта?{" "}
          <Link href="/register" className="font-medium text-[var(--primary)]">
            Регистрация по коду класса
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
