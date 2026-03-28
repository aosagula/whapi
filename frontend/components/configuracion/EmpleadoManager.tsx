"use client";

import { useEffect, useState } from "react";
import { apiFetch, ApiError } from "@/lib/api";
import { Empleado, PizzeriaRole } from "@/lib/types";

const ROLES: PizzeriaRole[] = ["admin", "cajero", "cocinero", "repartidor"];

const ROLE_LABEL: Record<PizzeriaRole, string> = {
  admin: "Admin",
  cajero: "Cajero",
  cocinero: "Cocinero",
  repartidor: "Repartidor",
};

const ROLE_COLOR: Record<PizzeriaRole, string> = {
  admin: "bg-purple-100 text-purple-700",
  cajero: "bg-blue-100 text-blue-700",
  cocinero: "bg-orange-100 text-orange-700",
  repartidor: "bg-teal-100 text-teal-700",
};

export default function EmpleadoManager({ pizzeriaId }: { pizzeriaId: string }) {
  const [empleados, setEmpleados] = useState<Empleado[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editingRole, setEditingRole] = useState<number | null>(null);

  // Formulario de invitación
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<PizzeriaRole>("cajero");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  async function load() {
    try {
      const data = await apiFetch<Empleado[]>(
        `/pizzerias/${pizzeriaId}/empleados`
      );
      setEmpleados(data);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cargar empleados");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, [pizzeriaId]);

  async function handleInvite(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true); setSaveError(null);
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/empleados`, {
        method: "POST",
        body: JSON.stringify({ name, email, password, role }),
      });
      setName(""); setEmail(""); setPassword(""); setRole("cajero");
      setShowForm(false);
      load();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Error al invitar empleado");
    } finally {
      setSaving(false);
    }
  }

  async function handleRoleChange(userId: number, newRole: PizzeriaRole) {
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/empleados/${userId}`, {
        method: "PATCH",
        body: JSON.stringify({ role: newRole }),
      });
      setEditingRole(null);
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al cambiar rol");
    }
  }

  async function handleRemove(userId: number, userName: string) {
    if (!confirm(`¿Revocar acceso de ${userName} a esta pizzería?`)) return;
    try {
      await apiFetch(`/pizzerias/${pizzeriaId}/empleados/${userId}`, {
        method: "DELETE",
      });
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Error al revocar acceso");
    }
  }

  if (loading) return <p className="py-8 text-center text-sm text-muted-foreground">Cargando…</p>;

  return (
    <div className="space-y-4 max-w-2xl">
      {error && (
        <p className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">{error}</p>
      )}

      {/* Lista de empleados */}
      {empleados.length === 0 && !showForm && (
        <p className="py-6 text-center text-sm text-muted-foreground">
          No hay empleados asignados a esta pizzería.
        </p>
      )}

      {empleados.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-border bg-white">
          {empleados.map((emp, idx) => (
            <div key={emp.id}>
              {idx > 0 && <div className="border-t border-border" />}
              <div className="flex items-center justify-between px-4 py-3 gap-4">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium">{emp.name}</span>
                    {editingRole === emp.id ? (
                      <select
                        defaultValue={emp.role}
                        onChange={(e) => handleRoleChange(emp.id, e.target.value as PizzeriaRole)}
                        onBlur={() => setEditingRole(null)}
                        autoFocus
                        className="rounded border border-primary px-2 py-0.5 text-xs focus:outline-none"
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>{ROLE_LABEL[r]}</option>
                        ))}
                      </select>
                    ) : (
                      <button
                        onClick={() => setEditingRole(emp.id)}
                        title="Clic para cambiar rol"
                        className={`rounded-full px-2.5 py-0.5 text-xs font-medium cursor-pointer hover:opacity-80 transition-opacity ${ROLE_COLOR[emp.role]}`}
                      >
                        {ROLE_LABEL[emp.role]}
                      </button>
                    )}
                  </div>
                  <p className="mt-0.5 text-xs text-muted-foreground">{emp.email}</p>
                </div>
                <button
                  onClick={() => handleRemove(emp.id, emp.name)}
                  className="flex-shrink-0 rounded-md border border-destructive/40 px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10 transition-colors"
                >
                  Revocar acceso
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Formulario de invitación */}
      {showForm ? (
        <form
          onSubmit={handleInvite}
          className="rounded-lg border border-primary/40 bg-white p-4 space-y-3"
        >
          <h4 className="font-semibold text-sm">Invitar empleado</h4>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div className="space-y-1">
              <label className="text-sm font-medium">Nombre *</label>
              <input type="text" required value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Juan García" className={inputCls} />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Email *</label>
              <input type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="juan@ejemplo.com" className={inputCls} />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Contraseña *</label>
              <input type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••" className={inputCls} />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">Rol *</label>
              <select value={role} onChange={(e) => setRole(e.target.value as PizzeriaRole)}
                className={inputCls}>
                {ROLES.map((r) => (
                  <option key={r} value={r}>{ROLE_LABEL[r]}</option>
                ))}
              </select>
            </div>
          </div>

          {saveError && <p className="text-sm text-destructive">{saveError}</p>}

          <div className="flex gap-2 justify-end">
            <button type="button"
              onClick={() => { setShowForm(false); setSaveError(null); }}
              className={btnOutline}>
              Cancelar
            </button>
            <button type="submit" disabled={saving} className={btnPrimary}>
              {saving ? "Guardando…" : "Invitar empleado"}
            </button>
          </div>
        </form>
      ) : (
        <button onClick={() => setShowForm(true)} className={btnPrimary}>
          + Invitar empleado
        </button>
      )}
    </div>
  );
}

const inputCls =
  "w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-ring";
const btnPrimary =
  "rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-60 transition-colors";
const btnOutline =
  "rounded-md border border-border px-4 py-2 text-sm hover:bg-secondary transition-colors";
