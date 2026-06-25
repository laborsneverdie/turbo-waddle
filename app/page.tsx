"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const educationOptions = ["大专", "双非本科", "211本科", "985本科", "211硕士", "985硕士", "博士"];

export default function HomePage() {
  const router = useRouter();
  const [form, setForm] = useState({
    city: "",
    degree: "",
    experience: "",
    field: "",
    certifications: "",
    email: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!form.city || !form.degree || !form.experience || !form.field) {
      setError("请填写所有字段");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.error || "提交失败");
      }

      router.push(`/history?userId=${data.userId}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "提交失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center">
      <div className="w-full max-w-lg">
        <h1 className="text-2xl font-bold text-center text-primary-700 mb-2">
          智能岗位推荐
        </h1>
        <p className="text-center text-slate-500 mb-8 text-sm">
          填写信息，获取最适合您的岗位推荐
        </p>

        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl shadow-md p-6 md:p-8 space-y-5"
        >
          {/* 所在城市 */}
          <div>
            <label htmlFor="city" className="block text-sm font-medium text-slate-700 mb-1.5">
              所在城市
            </label>
            <input
              id="city"
              name="city"
              type="text"
              placeholder="例如：北京"
              value={form.city}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
            />
          </div>

          {/* 最高学历 */}
          <div>
            <label htmlFor="degree" className="block text-sm font-medium text-slate-700 mb-1.5">
              最高学历
            </label>
            <select
              id="degree"
              name="degree"
              value={form.degree}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
            >
              <option value="">请选择学历</option>
              {educationOptions.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </div>

          {/* 工作经验 */}
          <div>
            <label htmlFor="experience" className="block text-sm font-medium text-slate-700 mb-1.5">
              工作经验
            </label>
            <input
              id="experience"
              name="experience"
              type="text"
              placeholder="例如：3年Java开发经验"
              value={form.experience}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
            />
          </div>

          {/* 求职方向 */}
          <div>
            <label htmlFor="field" className="block text-sm font-medium text-slate-700 mb-1.5">
              求职方向
            </label>
            <input
              id="field"
              name="field"
              type="text"
              placeholder="例如：财务、IT"
              value={form.field}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
            />
          </div>

          {/* 权威证书 */}
          <div>
            <label htmlFor="certifications" className="block text-sm font-medium text-slate-700 mb-1.5">
              权威证书
            </label>
            <input
              id="certifications"
              name="certifications"
              type="text"
              placeholder="例如：CPA、PMP、CFA"
              value={form.certifications}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
            />
          </div>

          {/* 邮箱 */}
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1.5">
              邮箱（选填）
            </label>
            <input
              id="email"
              name="email"
              type="email"
              placeholder="example@email.com"
              value={form.email}
              onChange={handleChange}
              className="w-full rounded-lg border border-slate-300 px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition"
            />
          </div>

          {/* 错误提示 */}
          {error && (
            <p className="text-red-500 text-sm text-center">{error}</p>
          )}

          {/* 提交按钮 */}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-primary-600 hover:bg-primary-700 disabled:bg-primary-400 text-white font-medium py-2.5 rounded-lg transition text-sm cursor-pointer disabled:cursor-not-allowed"
          >
            {loading ? "提交中..." : "提交"}
          </button>
        </form>
      </div>
    </div>
  );
}