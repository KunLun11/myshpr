import { api } from "@/lib/api";
import type { Me } from "@/types/api";

export interface RegisterStudentInput {
  invite_code: string;
  email: string;
  password: string;
  full_name: string;
}

export function loginRequest(email: string, password: string): Promise<Me> {
  return api.post<Me>("/auth/login", { email, password });
}

export function registerStudentRequest(input: RegisterStudentInput): Promise<Me> {
  return api.post<Me>("/auth/register/student", input);
}

export function logoutRequest(): Promise<void> {
  return api.post<void>("/auth/logout");
}

export function changePasswordRequest(
  currentPassword: string,
  newPassword: string,
): Promise<Me> {
  return api.post<Me>("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

// Concurrent calls share one in-flight refresh: refresh tokens rotate and a
// double rotation would trigger the backend's reuse detection.
let refreshInFlight: Promise<Me | null> | null = null;

export function refreshSession(): Promise<Me | null> {
  if (!refreshInFlight) {
    refreshInFlight = api
      .post<Me>("/auth/refresh")
      .catch(() => null)
      .finally(() => {
        refreshInFlight = null;
      });
  }
  return refreshInFlight;
}
