import { NextRequest, NextResponse } from 'next/server'

const COOKIE_SECRET = process.env.COOKIE_SECRET || 'vitte-admin-secret-key-change-me'

async function verifyToken(token: string): Promise<boolean> {
  try {
    const lastDot = token.lastIndexOf('.')
    if (lastDot === -1) return false

    const payload = token.substring(0, lastDot)
    const signature = token.substring(lastDot + 1)

    const encoder = new TextEncoder()
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(COOKIE_SECRET),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    )

    const sig = await crypto.subtle.sign('HMAC', key, encoder.encode(payload))
    const expected = Array.from(new Uint8Array(sig))
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('')

    return expected === signature
  } catch {
    return false
  }
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl

  // Allow login page, auth API, and health check
  if (
    pathname === '/admin-panel/login' ||
    pathname.startsWith('/admin-panel/api/auth/') ||
    pathname === '/admin-panel/api/health'
  ) {
    return NextResponse.next()
  }

  // Allow Next.js internals and static files
  if (pathname.startsWith('/admin-panel/_next/') || pathname.startsWith('/admin-panel/favicon')) {
    return NextResponse.next()
  }

  const session = req.cookies.get('admin_session')?.value

  if (!session || !(await verifyToken(session))) {
    const loginUrl = req.nextUrl.clone()
    loginUrl.pathname = '/admin-panel/login'
    return NextResponse.redirect(loginUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: '/admin-panel/:path*',
}
