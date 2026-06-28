import { NextResponse } from "next/server";
import { spawn } from "child_process";
import path from "path";

export async function POST() {
  try {
    const scriptPath = path.join(process.cwd(), "scripts", "recommend_jobs.py");

    const result = await new Promise<{ stdout: string; stderr: string; code: number | null }>(
      (resolve) => {
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
          resolve({ stdout, stderr, code });
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
