import { cookies } from "next/headers";

/**
 * Server-side access to the FastAPI service.
 *
 * Browser requests go through the same-origin Next proxy; server components
 * forward the incoming cookies explicitly (ADR-03).
 */
export const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

async function cookieHeader(): Promise<string> {
  const store = await cookies();
  return store
    .getAll()
    .map((cookie) => `${cookie.name}=${cookie.value}`)
    .join("; ");
}

export async function serverApiGet<T>(path: string): Promise<T | null> {
  const header = await cookieHeader();
  if (!header) {
    return null;
  }

  try {
    const response = await fetch(`${backendUrl}/api/v1${path}`, {
      headers: { cookie: header },
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}
