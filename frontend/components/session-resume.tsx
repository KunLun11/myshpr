"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { refreshSession } from "@/lib/auth-client";

/**
 * When a protected page redirects to `/login?next=...` because the access
 * cookie expired, try a silent refresh and return the user to where they
 * were going instead of forcing a password entry.
 */
export function SessionResume({ next }: { next: string }) {
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;

    void refreshSession().then((user) => {
      if (!cancelled && user) {
        router.replace(next);
        router.refresh();
      }
    });

    return () => {
      cancelled = true;
    };
  }, [next, router]);

  return null;
}
