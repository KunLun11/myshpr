"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { logoutRequest } from "@/lib/auth-client";

export function LogoutButton() {
  const router = useRouter();
  const [pending, setPending] = useState(false);

  async function handleLogout() {
    setPending(true);
    try {
      await logoutRequest();
    } catch {
      // The cookies are cleared client-side on navigation anyway; a failed
      // network call should not trap the user in the app.
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleLogout}
      disabled={pending}
      aria-label="Выйти из аккаунта"
    >
      <LogOut aria-hidden="true" />
      <span className="hidden sm:inline">{pending ? "Выходим…" : "Выйти"}</span>
    </Button>
  );
}
