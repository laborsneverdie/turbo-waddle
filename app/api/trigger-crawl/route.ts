import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";
import fs from "fs";

const PYTHON_EXE = "C:\\Users\\LEO\\.workbuddy\\binaries\\python\\versions\\3.11.15\\python.exe";
const LOG_DIR = path.join(process.cwd(), "logs");

/**
 * GET  /api/trigger-crawl?userId=4&city=长沙&field=财务会计
 * POST /api/trigger-crawl  body: {userId:4, city:"长沙", ...}
 */
export async function GET(req: NextRequest) {
  const params = Object.fromEntries(req.nextUrl.searchParams.entries());
  return handleCrawl(params);
}

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => ({}));
  return handleCrawl(body);
}

async function handleCrawl(params: Record<string, string>) {
  const userId = params.userId;
  const city = params.city;
  const field = params.field;

  if (!city || !field) {
    return NextResponse.json(
      { ok: false, msg: "缺少参数：city 和 field 为必填" },
      { status: 400 }
    );
  }

  // 确保日志目录存在
  fs.mkdirSync(LOG_DIR, { recursive: true });

  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const logFile = path.join(LOG_DIR, `crawl-${timestamp}.log`);

  const scriptPath = path.join(process.cwd(), "scripts", "recommend_jobs.py");

  // 立即返回，爬虫在后台异步运行
  const resolveNow = () => NextResponse.json({
    ok: true,
    msg: "爬虫已触发，正在后台运行。完成后微信会收到推送。",
    logFile: path.relative(process.cwd(), logFile),
    userId: userId || null,
    city,
    field,
  });

  return new Promise<NextResponse>((resolve) => {
    // 1 秒后立即返回，不等待爬虫完成
    const timeout = setTimeout(() => resolve(resolveNow()), 1000);
    const child = spawn(PYTHON_EXE, [scriptPath], {
      cwd: process.cwd(),
      env: {
        ...process.env,
        SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL || "",
        SUPABASE_SERVICE_ROLE_KEY: process.env.SUPABASE_SERVICE_ROLE_KEY || "",
        PUSHPLUS_TOKEN: process.env.PUSHPLUS_TOKEN || "",
        SMTP_HOST: process.env.SMTP_HOST || "",
        SMTP_PORT: process.env.SMTP_PORT || "465",
        SMTP_USER: process.env.SMTP_USER || "",
        SMTP_PASS: process.env.SMTP_PASS || "",
      },
      stdio: "pipe",
    });

    const logStream = fs.createWriteStream(logFile, { encoding: "utf-8" });
    let lastLine = "";

    child.stdout.on("data", (data: Buffer) => {
      const text = data.toString();
      logStream.write(text);
      lastLine = text.trim();
    });

    child.stderr.on("data", (data: Buffer) => {
      const text = data.toString();
      logStream.write(`[STDERR] ${text}`);
    });

    child.on("close", (code) => {
      logStream.write(`\n[完成] 退出码: ${code}\n`);
      logStream.end();
    });

    child.on("error", (err) => {
      logStream.write(`\n[错误] ${err.message}\n`);
      logStream.end();
    });
  });
}
