import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Pizzería Chatbot",
  description: "Plataforma de gestión de pedidos para pizzerías",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
