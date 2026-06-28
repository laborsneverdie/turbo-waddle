import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

// Vercel Serverless 函数最大执行时间（秒）
export const maxDuration = 60;

// Vercel Cron Jobs 发送 GET 请求
export async function GET() {
  return runRecommendScript();
}

// 手动触发用 POST
export async function POST() {
  return runRecommendScript();
}

async function runRecommendScript() {
  try {
    const scriptPath = path.join(process.cwd(), "scripts", "recommend_jobs.py");

    const result = await new Promise<{ stdout: string; stderr: string; code: number | null }>(
      (resolve) => {
        // 设置 55 秒超时，避免触碰 Vercel 60 秒限制
        const timeout = setTimeout(() => {
          resolve({
            stdout: "",
            stderr: "脚本执行超时（55秒）",
            code: -1,
          });
        }, 55000);

        const py = spawn("python", [scriptPath], {
          env: { ...process.env },
          shell: true,
        });

        let stdout = "";
        let stderr = "";

        py.stdout.on("data", (data) => {
          stdout += data.toString();
        });

        py.stderr.on("data", (data) => {
          stderr += data.toString();
        });

        py.on("close", (code) => {
          clearTimeout(timeout);
          resolve({ stdout, stderr, code });
        });

        py.on("error", (err) => {
          clearTimeout(timeout);
          resolve({
            stdout: "",
            stderr: `Python 环境不可用：${err.message}。在 Vercel 上请使用 GitHub Actions 触发。`,
            code: -1,
          });
        });
      }
    );

    if (result.code !== 0) {
      console.error("[cron] 脚本执行失败:", result.stderr);
      return NextResponse.json(
        { error: "脚本执行失败", detail: result.stderr },
        { status: 500 }
      );
    }

    return NextResponse.json({
      success: true,
      message: "推荐脚本执行成功",
      output: result.stdout,
    });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "服务器内部错误";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
