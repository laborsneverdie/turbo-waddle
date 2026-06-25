import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "岗位推荐",
  description: "智能岗位推荐平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-50">
        <header className="bg-primary-600 text-white shadow-md">
          <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
            <a href="/" className="text-xl font-bold tracking-wide">
              岗位推荐
            </a>
            <nav>
              <a
                href="/history"
                className="text-sm text-white/80 hover:text-white transition"
              >
                推荐历史
              </a>
            </nav>
          </div>
        </header>
        <main className="max-w-4xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}