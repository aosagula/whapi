/**
 * Middleware de Next.js: protege rutas autenticadas y redirige según estado de auth.
 * Usa una cookie `access_token` que el cliente setea al hacer login.
 */
import { NextResponse } from "next/server"
import type { NextRequest } from "next/server"

// Rutas que no requieren autenticación
const PUBLIC_PATHS = ["/", "/login", "/registro"]

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get("access_token")?.value

  const isPublic = PUBLIC_PATHS.some(
    (p) => pathname === p || pathname.startsWith(p + "/"),
  )

  // Rutas protegidas sin token → redirigir al login
  if (!isPublic && !token) {
    const loginUrl = new URL("/login", request.url)
    loginUrl.searchParams.set("redirect", pathname)
    return NextResponse.redirect(loginUrl)
  }

  // Ya autenticado en páginas de auth → redirigir al selector
  if (token && (pathname === "/login" || pathname === "/registro")) {
    return NextResponse.redirect(new URL("/selector", request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Excluye archivos estáticos, imágenes y las rutas de Next.js internos.
     */
    "/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)",
  ],
}
