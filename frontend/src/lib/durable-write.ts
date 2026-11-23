import { definitiveRejection, write } from "./api-client";
export type PendingWrite = { path: string; body: unknown; key: string };
export function pendingWrite(scope: string): PendingWrite | null {
  const raw = sessionStorage.getItem(`wq:request:${scope}`);
  return raw ? (JSON.parse(raw) as PendingWrite) : null;
}
/** Retain the exact request across ambiguous network failures and reloads. */
export async function durableWrite<T>(
  scope: string,
  path: string,
  body: unknown,
): Promise<T> {
  const key = `wq:request:${scope}`;
  const request = pendingWrite(scope) ?? {
    path,
    body,
    key: crypto.randomUUID(),
  };
  sessionStorage.setItem(key, JSON.stringify(request));
  try {
    const response = await write<T>(
      request.path,
      request.body,
      "POST",
      request.key,
    );
    sessionStorage.removeItem(key);
    return response;
  } catch (error) {
    if (definitiveRejection(error)) sessionStorage.removeItem(key);
    throw error;
  }
}
