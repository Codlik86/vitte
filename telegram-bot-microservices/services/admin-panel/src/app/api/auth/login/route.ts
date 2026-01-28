import { NextRequest, NextResponse } from 'next/server'
import crypto from 'crypto'

const ADMIN_USER = process.env.ADMIN_USER || 'admin'
const ADMIN_PASSWORD = process.env.ADMIN_PASSWORD || ''
const COOKIE_SECRET = process.env.COOKIE_SECRET || 'vitte-admin-secret-key-change-me'

function signToken(payload: string): string {
  const hmac = crypto.createHmac('sha256', COOKIE_SECRET)
  hmac.update(payload)
  return payload + '.' + hmac.digest('hex')
}

export async function POST(req: NextRequest) {
  try {
    const { username, password } = await req.json()

    if (username !== ADMIN_USER || password !== ADMIN_PASSWORD) {
      return NextResponse.json({ error: 'Invalid credentials' }, { status: 401 })
    }

    const payload = JSON.stringify({ user: username, ts: Date.now() })
    const token = signToken(Buffer.from(payload).toString('base64'))

    const response = NextResponse.json({ ok: true })
    response.cookies.set('admin_session', token, {
      httpOnly: true,
      secure: false,
      sameSite: 'lax',
      path: '/admin-panel',
      maxAge: 60 * 60 * 24 * 7, // 7 days
    })

    return response
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 400 })
  }
}
