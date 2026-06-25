import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/supabaseClient";

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

    const { data, error } = await getSupabase()
      .from("user_profiles")
      .insert([
        {
          city,
          degree,
          experience,
          field,
          certifications: certifications || null,
          email: email || null,
        },
      ])
      .select("id")
      .single();

    if (error) {
      throw new Error(error.message);
    }

    return NextResponse.json({ userId: data.id }, { status: 201 });
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "服务器内部错误";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}