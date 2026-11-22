import { env } from "@/lib/env";

export interface FieldError {
  field: string;
  message: string;
}

/** Error carrying the backend's machine-readable `code` (RFC 7807-ish). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly errors: FieldError[];

  constructor(status: number, code: string, message: string, errors: FieldError[] = []) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.errors = errors;
  }
}

type Init = Omit<RequestInit, "body"> & { body?: unknown };

export async function apiFetch<T>(path: string, init: Init = {}): Promise<T> {
  const { body, headers, ...rest } = init;
  const response = await fetch(`${env.apiBase}${path}`, {
    credentials: "include",
    ...rest,
    headers: {
      ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
      ...headers,
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const problem = await response.json().catch(() => ({}));
    throw new ApiError(
      response.status,
      problem.code ?? "UNKNOWN_ERROR",
      problem.detail ?? response.statusText,
      problem.errors ?? [],
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "POST", body }),
  patch: <T>(path: string, body?: unknown) => apiFetch<T>(path, { method: "PATCH", body }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: "DELETE" }),
};
