import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

/**
 * GET /api/trigger-crawl
 * 访问即触发 Python 爬虫脚本，异步执行，立即返回
 */
export async function GET() {
  const scriptPath = path.join(process.cwd(), "scripts", "recommend_jobs.py");

  const child = spawn("python", [scriptPath], {
    detached: true,
    stdio: "ignore",
    cwd: process.cwd(),
    env: { ...process.env },
  });

  child.on("error", (err) => {
    console.error("[爬虫] 启动失败:", err.message);
  });

  child.on("spawn", () => {
    console.log(`[爬虫] 已触发，PID: ${child.pid}`);
  });

  // 脱离父进程，父进程退出不影响爬虫
  child.unref();

  return NextResponse.json({
    message: "爬虫已触发，推荐将在几分钟内生成并推送至微信/邮箱",
    pid: child.pid,
  });
}
