const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api/v1";

export class ApiError extends Error {
  status: number;
  data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem("fasalflow_token");
}

export function setStoredToken(token: string): void {
  localStorage.setItem("fasalflow_token", token);
}

export function clearStoredToken(): void {
  localStorage.removeItem("fasalflow_token");
  localStorage.removeItem("fasalflow_user");
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}`;
    let errorData = null;
    try {
      errorData = await response.json();
      if (errorData && typeof errorData.detail === "string") {
        errorMessage = errorData.detail;
      } else if (errorData && typeof errorData.message === "string") {
        errorMessage = errorData.message;
      }
    } catch {
      // response wasn't JSON
    }
    throw new ApiError(response.status, errorMessage, errorData);
  }

  // 204 No Content
  if (response.status === 204) {
    return {} as T;
  }

  return response.json() as Promise<T>;
}
