import { NextRequest, NextResponse } from "next/server";
import { queryOne } from "@/lib/db";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { city, degree, experience, field, certifications, email } = body;

    if (!city || !degree || !experience || !field) {
      return NextResponse.json(
        { error: "所有字段都是必填的" },
        { status: 400 }
      );
    }

    const data = await queryOne<{ id: number }>(
      `INSERT INTO public.user_profiles (city, degree, experience, field, certifications, email)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id`,
      [city, degree, experience, field, certifications || null, email || null]
    );

    if (!data) {
      throw new Error("插入用户资料失败");
    }

    return NextResponse.json({ userId: data.id }, { status: 201 });
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "服务器内部错误";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
