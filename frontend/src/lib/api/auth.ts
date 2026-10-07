import { apiClient, setStoredToken, clearStoredToken, getStoredToken } from "./client";

export { getStoredToken };

export type UserRole = "FARMER" | "COLD_STORE_OPERATOR";

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: UserRole;
}

export interface UserProfile {
  id: number;
  name: string;
  identifier: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  farmer_id?: number | null;
  operator_id?: number | null;
  district?: string | null;
}

export interface LoginPayload {
  identifier: string;
  password: string;
}

export interface RegisterPayload {
  name: string;
  identifier: string;
  password: string;
  role: UserRole;
  district: string;
  block?: string;
  village?: string;
  phone?: string;
  organization_name?: string;
}

export async function loginUser(payload: LoginPayload): Promise<TokenResponse> {
  const data = await apiClient<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setStoredToken(data.access_token);
  return data;
}

export async function registerUser(payload: RegisterPayload): Promise<TokenResponse> {
  const data = await apiClient<TokenResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setStoredToken(data.access_token);
  return data;
}

export async function getCurrentUser(): Promise<UserProfile> {
  const user = await apiClient<UserProfile>("/auth/me");
  localStorage.setItem("fasalflow_user", JSON.stringify(user));
  return user;
}

export function getCachedUser(): UserProfile | null {
  const raw = localStorage.getItem("fasalflow_user");
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function logout(): void {
  clearStoredToken();
}
