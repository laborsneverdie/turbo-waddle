"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

interface JobRecommendation {
  id: number;
  job_title: string;
  company: string;
  enterprise_type: string;
  match_score: number;
  detail_link: string;
  user_id: number;
}

function HistoryContent() {
  const searchParams = useSearchParams();
  const userId = searchParams.get("userId");
  const [recommendations, setRecommendations] = useState<JobRecommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userId) {
      setError("缺少用户ID");
      setLoading(false);
      return;
    }

    const fetchRecommendations = async () => {
      try {
        const res = await fetch(`/api/recommendations?userId=${userId}`);
        const data = await res.json();

        if (!res.ok) {
          throw new Error(data.error || "获取推荐失败");
        }

        setRecommendations(data.recommendations);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "获取推荐失败，请稍后重试");
      } finally {
        setLoading(false);
      }
    };

    fetchRecommendations();
  }, [userId]);

  const getCompanyTypeBadge = (type: string) => {
    const map: Record<string, string> = {
      "国企": "bg-red-100 text-red-700",
      "私企": "bg-blue-100 text-blue-700",
      "外企": "bg-green-100 text-green-700",
    };
    return map[type] || "bg-gray-100 text-gray-700";
  };

  const getMatchColor = (score: number) => {
    if (score >= 80) return "text-green-600";
    if (score >= 60) return "text-yellow-600";
    return "text-red-500";
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-center text-primary-700 mb-2">
        推荐历史
      </h1>
      <p className="text-center text-slate-500 mb-8 text-sm">
        以下是为您匹配的岗位推荐
      </p>

      {loading && (
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        </div>
      )}

      {error && (
        <div className="text-center py-12">
          <p className="text-red-500">{error}</p>
        </div>
      )}

      {!loading && !error && recommendations.length === 0 && (
        <div className="text-center py-12">
          <p className="text-slate-400">暂无推荐记录</p>
        </div>
      )}

      {!loading && !error && recommendations.length > 0 && (
        <div className="grid gap-4 sm:grid-cols-2">
          {recommendations.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl shadow-sm border border-slate-100 p-5 hover:shadow-md transition"
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-800 text-base">
                    {item.job_title}
                  </h3>
                  <p className="text-xs text-slate-500 mt-0.5">{item.company}</p>
                </div>
                <span
                  className={`text-xs font-medium px-2 py-0.5 rounded-full shrink-0 ${getCompanyTypeBadge(item.enterprise_type)}`}
                >
                  {item.enterprise_type}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs text-slate-500">匹配度</span>
                  <span className={`text-lg font-bold ${getMatchColor(item.match_score)}`}>
                    {item.match_score}%
                  </span>
                </div>
                <a
                  href={item.detail_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-primary-600 hover:text-primary-700 font-medium transition"
                >
                  查看详情 →
                </a>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="text-center mt-8">
        <a
          href="/"
          className="text-sm text-primary-600 hover:text-primary-700 transition"
        >
          ← 返回首页
        </a>
      </div>
    </div>
  );
}

export default function HistoryPage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-12">
          <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
        </div>
      }
    >
      <HistoryContent />
    </Suspense>
  );
}