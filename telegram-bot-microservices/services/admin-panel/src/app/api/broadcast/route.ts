import { NextRequest, NextResponse } from 'next/server'

const ADMIN_API = process.env.ADMIN_API_URL || 'http://admin:8080'

// GET /api/broadcast - список рассылок
export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url)
    const status = searchParams.get('status') || ''
    const broadcast_type = searchParams.get('type') || ''
    const limit = searchParams.get('limit') || '50'
    const offset = searchParams.get('offset') || '0'

    const params = new URLSearchParams()
    if (status) params.append('status', status)
    if (broadcast_type) params.append('broadcast_type', broadcast_type)
    params.append('limit', limit)
    params.append('offset', offset)

    const res = await fetch(`${ADMIN_API}/broadcast/list?${params}`, { cache: 'no-store' })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}

// POST /api/broadcast - создание рассылки
export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const res = await fetch(`${ADMIN_API}/broadcast/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
