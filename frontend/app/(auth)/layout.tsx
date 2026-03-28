/**
 * Layout para páginas de autenticación (login, registro).
 * Sin sidebar, centrado, fondo crema con decoración de marca.
 */
export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-hero-warm flex flex-col items-center justify-center px-4 py-12">
      {/* Logo/marca */}
      <a href="/" className="font-serif text-3xl text-brown mb-10 hover:text-brand transition-colors">
        Whapi
      </a>
      <div className="w-full max-w-md">{children}</div>
    </div>
  )
}
