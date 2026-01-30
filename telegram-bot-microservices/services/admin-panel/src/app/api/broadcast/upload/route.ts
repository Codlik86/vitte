import { NextRequest, NextResponse } from 'next/server'

const ADMIN_API = process.env.ADMIN_API_URL || 'http://admin:8080'

// POST /api/broadcast/upload - загрузка медиа файла
export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData()

    const res = await fetch(`${ADMIN_API}/broadcast/upload`, {
      method: 'POST',
      body: formData,
    })

    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (e: any) {
    return NextResponse.json({ error: e.message }, { status: 500 })
  }
}
