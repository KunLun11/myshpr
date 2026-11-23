import { cache } from "react";
import { redirect } from "next/navigation";

import { homeForRole } from "@/lib/roles";
import { serverApiGet } from "@/lib/server-api";
import type { Me, UserRole } from "@/types/api";

/** Request-scoped session read (deduplicated across the render tree). */
export const getCurrentUser = cache((): Promise<Me | null> => {
  return serverApiGet<Me>("/auth/me");
});

export async function requireUser(): Promise<Me> {
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login");
  }
  return user;
}

export async function requireRole(...roles: UserRole[]): Promise<Me> {
  const user = await requireUser();
  if (user.role !== "super_admin" && !roles.includes(user.role)) {
    redirect(homeForRole(user.role));
  }
  return user;
}
