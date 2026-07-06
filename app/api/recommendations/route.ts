import { NextRequest, NextResponse } from "next/server";
import { query } from "@/lib/db";

interface JobRecommendation {
  id: number;
  job_title: string;
  company: string;
  enterprise_type: string;
  match_score: number;
  detail_link: string;
  user_id: number;
  created_at: string;
}

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const userId = searchParams.get("userId");

  if (!userId) {
    return NextResponse.json(
      { error: "缺少用户ID参数" },
      { status: 400 }
    );
  }

  try {
    const data = await query<JobRecommendation>(
      `SELECT * FROM public.job_recommendations
       WHERE user_id = $1
       ORDER BY created_at DESC`,
      [userId]
    );

    return NextResponse.json({ recommendations: data });
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "服务器内部错误";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
