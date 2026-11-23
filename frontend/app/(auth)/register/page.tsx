import type { Metadata } from "next";
import { Suspense } from "react";

import { Skeleton } from "@/components/ui/skeleton";

import { RegisterForm } from "./register-form";

export const metadata: Metadata = { title: "Регистрация" };
export const instant = false;

export default function RegisterPage() {
  return (
    <Suspense fallback={<AuthCardSkeleton />}>
      <RegisterForm />
    </Suspense>
  );
}

function AuthCardSkeleton() {
  return (
    <div className="w-full" aria-busy="true" aria-live="polite">
      <Skeleton className="h-8 w-40" />
      <Skeleton className="mt-3 h-4 w-full" />
      <Skeleton className="mt-6 h-80 w-full" />
    </div>
  );
}
