import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Вход" };
export const instant = false;

export default function LoginPage() {
  return (
    <Suspense fallback={<AuthCardSkeleton />}>
      <LoginForm />
    </Suspense>
  );
}

function AuthCardSkeleton() {
  return (
    <div className="w-full" aria-busy="true" aria-live="polite">
      <Skeleton className="h-8 w-32" />
      <Skeleton className="mt-3 h-4 w-full" />
      <Skeleton className="mt-6 h-64 w-full" />
    </div>
  );
}
