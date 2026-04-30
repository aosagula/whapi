"use client"

import { useEffect, useState } from "react"
import { useParams } from "next/navigation"
import { Bot, Save } from "lucide-react"
import { api, ApiError } from "@/lib/api"

type FormState = {
  assistant_name: string
  assistant_system_prompt_master: string
  assistant_system_prompt_default: string
}

const INITIAL_STATE: FormState = {
  assistant_name: "",
  assistant_system_prompt_master: "",
  assistant_system_prompt_default: "",
}

export default function AsistenteSettingsPage() {
  const params = useParams()
  const comercioId = params.comercio_id as string

  const [form, setForm] = useState<FormState>(INITIAL_STATE)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const comercio = await api.comercios.detalle(comercioId)
        if (!active) return
        setForm({
          assistant_name: comercio.assistant_name ?? "",
          assistant_system_prompt_master: comercio.assistant_system_prompt_master ?? "",
          assistant_system_prompt_default: comercio.assistant_system_prompt_default ?? "",
        })
      } catch {
        if (!active) return
        setError("No se pudo cargar la configuración del asistente.")
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    return () => {
      active = false
    }
  }, [comercioId])

  function updateField<K extends keyof FormState>(field: K, value: FormState[K]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)

    try {
      await api.comercios.editar(comercioId, {
        assistant_name: form.assistant_name.trim(),
        assistant_system_prompt_master: form.assistant_system_prompt_master.trim(),
        assistant_system_prompt_default: form.assistant_system_prompt_default.trim(),
      })
      setSuccess("Configuración guardada.")
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Solo el dueño del comercio puede editar esta configuración.")
      } else {
        setError("No se pudo guardar la configuración del asistente.")
      }
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="py-16 flex flex-col items-center gap-3 text-brown-muted">
        <div className="w-6 h-6 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm">Cargando configuración del asistente...</span>
      </div>
    )
  }

  return (
    <div className="max-w-4xl">
      <div className="mb-6">
        <div className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700">
          <Bot className="h-3.5 w-3.5" />
          Ajustes del asistente
        </div>
        <h1 className="mt-3 font-serif text-3xl text-brown">Asistente</h1>
        <p className="mt-1 text-sm text-brown-muted">
          Configurá el nombre visible del asistente y sus prompts base para el comercio.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="rounded-2xl border border-stone-200 bg-white shadow-sm">
        <div className="border-b border-stone-100 px-6 py-5">
          <label className="block text-sm font-medium text-brown" htmlFor="assistant_name">
            Nombre del asistente
          </label>
          <input
            id="assistant_name"
            type="text"
            value={form.assistant_name}
            onChange={(e) => updateField("assistant_name", e.target.value)}
            placeholder="Ej: Pizzaiolo IA"
            className="mt-2 w-full rounded-xl border border-stone-200 px-4 py-2.5 text-sm text-brown outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
          />
        </div>

        <div className="grid gap-0 md:grid-cols-2">
          <div className="border-b border-stone-100 px-6 py-5 md:border-b-0 md:border-r">
            <label className="block text-sm font-medium text-brown" htmlFor="assistant_system_prompt_master">
              System prompt maestro
            </label>
            <p className="mt-1 text-xs text-brown-muted">
              Instrucciones globales del comercio, tono, reglas y políticas.
            </p>
            <textarea
              id="assistant_system_prompt_master"
              value={form.assistant_system_prompt_master}
              onChange={(e) => updateField("assistant_system_prompt_master", e.target.value)}
              rows={14}
              placeholder="Definí el comportamiento principal del asistente..."
              className="mt-3 w-full rounded-xl border border-stone-200 px-4 py-3 text-sm text-brown outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
            />
          </div>

          <div className="px-6 py-5">
            <label className="block text-sm font-medium text-brown" htmlFor="assistant_system_prompt_default">
              System prompt por defecto
            </label>
            <p className="mt-1 text-xs text-brown-muted">
              Base reusable para conversaciones nuevas antes de agregar contexto dinámico.
            </p>
            <textarea
              id="assistant_system_prompt_default"
              value={form.assistant_system_prompt_default}
              onChange={(e) => updateField("assistant_system_prompt_default", e.target.value)}
              rows={14}
              placeholder="Definí el prompt base del asistente..."
              className="mt-3 w-full rounded-xl border border-stone-200 px-4 py-3 text-sm text-brown outline-none transition focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
            />
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 border-t border-stone-100 px-6 py-4">
          <div className="text-sm">
            {error && <span className="text-red-600">{error}</span>}
            {!error && success && <span className="text-green-700">{success}</span>}
            {!error && !success && <span className="text-brown-muted">Los cambios impactan en futuros flujos del asistente.</span>}
          </div>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-amber-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Save className="h-4 w-4" />
            {saving ? "Guardando..." : "Guardar"}
          </button>
        </div>
      </form>
    </div>
  )
}
