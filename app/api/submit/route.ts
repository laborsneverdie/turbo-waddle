import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/db";
import { spawn } from "child_process";
import path from "path";

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
      .insert({
        city,
        degree,
        experience,
        field,
        certifications: certifications || null,
        email: email || null,
      })
      .select("id")
      .single();

    if (error || !data) {
      throw new Error(error?.message || "插入用户资料失败");
    }

    // 提交成功后，异步触发本地 Python 爬虫（内网部署）
    triggerCrawl(data.id);

    return NextResponse.json(
      {
        userId: data.id,
        message: "提交成功！爬虫已开始工作，岗位推荐将在几分钟内生成并发送至您的微信/邮箱",
      },
      { status: 201 }
    );
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "服务器内部错误";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/** 触发本地 Python 爬虫脚本（异步，不阻塞请求） */
function triggerCrawl(userId: number) {
  const scriptPath = path.join(process.cwd(), "scripts", "recommend_jobs.py");

  const child = spawn("python", [scriptPath], {
    detached: true,
    stdio: "ignore",
    cwd: process.cwd(),
    env: { ...process.env },
  });

  child.on("error", (err) => {
    console.error(`[爬虫] 用户${userId} 触发失败:`, err.message);
  });

  child.on("spawn", () => {
    console.log(`[爬虫] 用户${userId}提交后已触发，PID: ${child.pid}`);
  });

  child.unref();
}
