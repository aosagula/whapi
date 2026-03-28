import type { Metadata } from "next"
import { DM_Sans, DM_Serif_Display } from "next/font/google"
import "./globals.css"

// Fuente sans-serif para cuerpo de texto
const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
})

// Fuente serif para titulares (alternativa a Fraunces, misma calidez editorial)
const dmSerifDisplay = DM_Serif_Display({
  subsets: ["latin"],
  weight: "400",
  variable: "--font-dm-serif",
  display: "swap",
})

export const metadata: Metadata = {
  title: "Whapi — Pedidos por WhatsApp",
  description:
    "Plataforma multi-tenant para gestionar pedidos de WhatsApp con chatbot inteligente y panel web en tiempo real.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="es" className={`${dmSans.variable} ${dmSerifDisplay.variable}`}>
      <body className="font-sans">{children}</body>
    </html>
  )
}
