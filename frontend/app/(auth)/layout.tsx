import Link from "next/link";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="mx-auto w-full max-w-5xl px-6 py-6">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          Индивидуальный проект
        </Link>
      </header>
      <main className="mx-auto flex w-full max-w-md flex-1 items-start px-6 pb-16 pt-4 sm:items-center">
        {children}
      </main>
    </div>
  );
}
