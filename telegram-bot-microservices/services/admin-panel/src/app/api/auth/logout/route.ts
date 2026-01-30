import { NextResponse } from 'next/server'

export async function POST() {
  const response = NextResponse.json({ ok: true })
  response.cookies.set('admin_session', '', {
    httpOnly: true,
    secure: false,
    sameSite: 'lax',
    path: '/admin-panel',
    maxAge: 0,
  })
  return response
}
