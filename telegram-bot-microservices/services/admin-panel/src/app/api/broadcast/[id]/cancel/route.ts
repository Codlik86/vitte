import { NextRequest, NextResponse } from 'next/server'

const ADMIN_API = process.env.ADMIN_API_URL || 'http://admin:8080'

// POST /api/broadcast/[id]/cancel - отменить рассылку
export async function POST(req: NextRequest, { params }: { params: { id: string } }) {
  try {
    const res = await fetch(`${ADMIN_API}/broadcast/${params.id}/cancel`, {
      method: 'POST',
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
