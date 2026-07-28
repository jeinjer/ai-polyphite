const DEFAULT_API_BASE_URL = "http://127.0.0.1:8000";

export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_BASE_URL,
);

function normalizeApiBaseUrl(value: string): string {
  const url = new URL(value);
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new Error("NEXT_PUBLIC_API_URL must use HTTP or HTTPS.");
  }
  if (url.pathname !== "/" || url.search || url.hash) {
    throw new Error("NEXT_PUBLIC_API_URL must contain only an origin.");
  }
  return url.origin;
}
