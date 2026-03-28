/** Clave bajo la que se guarda el JWT en localStorage. */
const TOKEN_KEY = "token";
/** Clave para el pizzeria_id activo. */
const PIZZERIA_KEY = "pizzeria_id";
/** Clave para el rol del usuario activo. */
const ROLE_KEY = "role";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getPizzeriaId(): number | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem(PIZZERIA_KEY);
  if (!raw) return null;
  const n = parseInt(raw, 10);
  return isNaN(n) ? null : n;
}

export function setPizzeriaId(id: number): void {
  localStorage.setItem(PIZZERIA_KEY, String(id));
}

export function getRole(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ROLE_KEY);
}

export function setRole(role: string): void {
  localStorage.setItem(ROLE_KEY, role);
}

export function clearAuth(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(PIZZERIA_KEY);
  localStorage.removeItem(ROLE_KEY);
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

export function hasPizzeriaSelected(): boolean {
  return getPizzeriaId() !== null;
}
