import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/db";
import { spawn, exec } from "child_process";
import path from "path";
import fs from "fs";

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

    // 杀死旧 Python 进程，再触发新爬虫
    killOldCrawlers(() => {
      triggerCrawl(data.id, city, field);
    });

    // 查找最新 H5 链接
    const latestH5 = findLatestH5();

    return NextResponse.json(
      {
        userId: data.id,
        message: "提交成功！旧爬虫已清除，新爬虫已启动。完成后微信会收到推送。",
        latestH5: latestH5 || null,
      },
      { status: 201 }
    );
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "服务器内部错误";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/** 杀死所有旧 Python 进程，回调后触发新爬虫 */
function killOldCrawlers(callback: () => void) {
  exec("taskkill /F /IM python.exe 2>nul", (err) => {
    // 延迟 1 秒确保进程完全关闭
    setTimeout(callback, 1000);
  });
}

/** 触发本地 Python 爬虫 */
function triggerCrawl(userId: number, city: string, field: string) {
  const pythonExe = "C:\\Users\\LEO\\.workbuddy\\binaries\\python\\versions\\3.11.15\\python.exe";
  const scriptPath = path.join(process.cwd(), "scripts", "recommend_jobs.py");

  const child = spawn(pythonExe, [scriptPath], {
    detached: true,
    stdio: "pipe",
    cwd: process.cwd(),
    env: {
      ...process.env,
      SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || "",
      SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY || "",
      PUSHPLUS_TOKEN: process.env.PUSHPLUS_TOKEN || "",
    },
  });

  child.stderr.on("data", (data: Buffer) => {
    const text = data.toString().trim();
    if (text) console.error(`[爬虫错误] ${text.slice(0, 200)}`);
  });

  child.on("close", (code) => {
    console.log(`[爬虫] 用户${userId}的爬虫完成，退出码: ${code}`);
    // 完成后更新 H5 链接，写入一个 status 文件供前端读取
    const latest = findLatestH5();
    if (latest) {
      fs.writeFileSync(
        path.join(process.cwd(), "public", "crawl_status.json"),
        JSON.stringify({ done: true, latestH5: latest, timestamp: Date.now() })
      );
    }
  });

  child.on("error", (err) => {
    console.error(`[爬虫] 启动失败:`, err.message);
  });
}

/** 查找最新生成的 H5 文件，返回可访问的 URL */
function findLatestH5(): string | null {
  const reportsDir = path.join(process.cwd(), "reports");
  if (!fs.existsSync(reportsDir)) return null;
  const files = fs.readdirSync(reportsDir)
    .filter(f => f.startsWith("job_h5_") && f.endsWith(".html"))
    .sort()
    .reverse();
  if (files.length === 0) return null;
  return `/latest-h5.html`;
}
