export const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function readJsonResponse(response) {
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload?.message ?? "Request failed");
  }

  return payload;
}
