import type { UserRole } from "@/types/api";

export const ROLE_LABELS: Record<UserRole, string> = {
  student: "Ученик",
  teacher: "Учитель",
  school_admin: "Администратор школы",
  super_admin: "Суперадмин",
};

/** Where a user lands after a successful login. */
export function homeForRole(role: UserRole): string {
  switch (role) {
    case "student":
      return "/cabinet";
    case "teacher":
      return "/teacher";
    case "school_admin":
    case "super_admin":
      return "/admin";
  }
}
