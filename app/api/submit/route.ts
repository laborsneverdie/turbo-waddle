import { NextRequest, NextResponse } from "next/server";
import { getSupabase } from "@/lib/db";

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

    // 提交成功后，异步触发 GitHub Actions（10分钟内完成首次推荐）
    triggerWorkflow(data.id).catch((e) => {
      console.error("[GitHub Actions] 触发失败:", e);
    });

    return NextResponse.json(
      {
        userId: data.id,
        message: "提交成功，岗位推荐将在10分钟内生成并发送至您的邮箱",
      },
      { status: 201 }
    );
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : "服务器内部错误";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/**
 * 触发 GitHub Actions workflow，让推荐脚本在10分钟内运行
 * 需要 GITHUB_TOKEN 和 GITHUB_REPO 环境变量
 */
async function triggerWorkflow(userId: number) {
  const token = process.env.GITHUB_TOKEN;
  const repo = process.env.GITHUB_REPO; // 格式: owner/repo

  if (!token || !repo) {
    console.log("[GitHub Actions] 未配置 GITHUB_TOKEN 或 GITHUB_REPO，跳过自动触发");
    return;
  }

  const resp = await fetch(
    `https://api.github.com/repos/${repo}/actions/workflows/job-recommend.yml/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github.v3+json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ref: "main" }),
    }
  );

  if (resp.status === 204) {
    console.log(`[GitHub Actions] 触发成功，用户 ${userId} 的推荐将在10分钟内生成`);
  } else {
    const text = await resp.text();
    console.error(`[GitHub Actions] 触发失败 HTTP ${resp.status}: ${text}`);
  }
}
