import { NextRequest, NextResponse } from 'next/server'

const ADMIN_API = process.env.ADMIN_API_URL || 'http://admin:8080'

// GET /api/broadcast/active - активные рассылки для мониторинга
export async function GET(req: NextRequest) {
  try {
    const res = await fetch(`${ADMIN_API}/broadcast/active`, { cache: 'no-store' })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
