const API_BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function readJsonResponse(response) {
  const payload = await response.json();

  if (!response.ok) {
    throw new Error(payload?.message ?? "Request failed");
  }

  return payload;
}

export async function predictSoil(data) {
  const response = await fetch(`${API_BASE_URL}/soil/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  return readJsonResponse(response);
}

export async function predictDisease(imageFile) {
  const formData = new FormData();
  formData.append("image", imageFile);

  const response = await fetch(`${API_BASE_URL}/disease/predict`, {
    method: "POST",
    body: formData,
  });

  return readJsonResponse(response);
}
