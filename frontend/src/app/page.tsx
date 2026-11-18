"use client";

import React, { useState, useEffect } from "react";
import { AppleNavbar } from "@/components/apple-navbar";
import { StudentModule } from "@/components/modules/StudentModule";
import { TeacherModule } from "@/components/modules/TeacherModule";
import { TrendsModule } from "@/components/modules/TrendsModule";
import { MLOpsModule } from "@/components/modules/MLOpsModule";
import { 
  GraduationCap, 
  Users, 
  TrendingUp, 
  Cpu, 
  Sparkles, 
  ChevronRight
} from "lucide-react";

export default function Home() {
  const [activeModule, setActiveModule] = useState<number>(1);
  const [isDark, setIsDark] = useState<boolean>(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  return (
    <div className="min-h-screen bg-[#f5f5f7] dark:bg-black text-[#1d1d1f] dark:text-[#f5f5f7] flex flex-col transition-colors duration-200">
      {/* Top Navbar */}
      <AppleNavbar 
        activeModule={activeModule}
        setActiveModule={setActiveModule}
        isDark={isDark}
        toggleDark={() => setIsDark(!isDark)}
      />

      {/* Editorial Header (Apple Typography - Zero AI Slop) */}
      <section className="pt-8 pb-6 px-4 sm:px-6 lg:px-8 border-b border-black/[0.06] dark:border-white/[0.08]">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-6">
            <div className="space-y-1.5 max-w-2xl">
              <span className="text-[12px] font-bold uppercase tracking-wider text-[#0071e3] dark:text-[#0a84ff] block">
                Phân Tích Dữ Liệu Lớn & Tuyển Sinh Đại Học
              </span>
              <h1 className="text-3xl sm:text-4xl font-bold tracking-tight text-[#1d1d1f] dark:text-white leading-tight">
                Xác suất trúng tuyển theo thời gian thực.
              </h1>
              <p className="text-[14px] sm:text-[15px] text-[#6e6e73] dark:text-[#a1a1a6] leading-relaxed pt-0.5">
                Huấn luyện trên 9.66 triệu hồ sơ thi THPT, mô hình hóa dải phân vị chuẩn qua LightGBM Quantile Regression và đối soát chu kỳ Google Trends mùa thi.
              </p>
            </div>

            {/* Apple Minimalist Key Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3 lg:shrink-0">
              <div className="p-3.5 rounded-2xl apple-glass text-center">
                <span className="text-[10px] text-[#86868b] block font-semibold uppercase tracking-wider">Hồ sơ thi</span>
                <span className="text-xl font-bold tnum text-[#1d1d1f] dark:text-white">9.66M+</span>
                <span className="text-[10px] text-[#86868b] block mt-0.5">Bộ GD&ĐT</span>
              </div>
              <div className="p-3.5 rounded-2xl apple-glass text-center">
                <span className="text-[10px] text-[#86868b] block font-semibold uppercase tracking-wider">Độ trễ phục vụ</span>
                <span className="text-xl font-bold tnum text-[#34c759] dark:text-[#30d158]">15.8ms</span>
                <span className="text-[10px] text-[#86868b] block mt-0.5">p50 Serving</span>
              </div>
              <div className="p-3.5 rounded-2xl apple-glass text-center">
                <span className="text-[10px] text-[#86868b] block font-semibold uppercase tracking-wider">Đặc trưng ML</span>
                <span className="text-xl font-bold tnum text-[#af52de] dark:text-[#bf5af2]">15 Features</span>
                <span className="text-[10px] text-[#86868b] block mt-0.5">Contract 3.0</span>
              </div>
              <div className="p-3.5 rounded-2xl apple-glass text-center">
                <span className="text-[10px] text-[#86868b] block font-semibold uppercase tracking-wider">Độ tương quan</span>
                <span className="text-xl font-bold tnum text-[#ff9500] dark:text-[#ff9f0a]">0.9106</span>
                <span className="text-[10px] text-[#86868b] block mt-0.5">Spearman Rho</span>
              </div>
            </div>
          </div>

          {/* Module Navigation Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
            {[
              {
                id: 1,
                title: "1. Thí Sinh & Cá Nhân Hóa",
                desc: "Dự báo đỗ, giỏ nguyện vọng 20-50-30, mô phỏng What-If & vị thế CDF",
                icon: GraduationCap,
                color: "#0071e3"
              },
              {
                id: 2,
                title: "2. Giáo Viên & Lớp Học",
                desc: "Tư vấn hàng loạt đoàn thể, phân tích phổ điểm lớp & đối đầu trường",
                icon: Users,
                color: "#5856d6"
              },
              {
                id: 3,
                title: "3. Google Trends & Big Data",
                desc: "Radar nhịp mùa thi, độ nóng nhóm ngành & tương quan Trends vs Điểm chuẩn",
                icon: TrendingUp,
                color: "#ff9500"
              },
              {
                id: 4,
                title: "4. MLOps & Chấm Điểm",
                desc: "Lakehouse Monitor, tra cứu CDF <10ms, kiểm định sai số OOT & API Serving",
                icon: Cpu,
                color: "#af52de"
              },
            ].map((card) => {
              const Icon = card.icon;
              const isCurrent = activeModule === card.id;
              return (
                <div
                  key={card.id}
                  onClick={() => setActiveModule(card.id)}
                  className={`p-4 rounded-2xl cursor-pointer transition-all duration-150 relative ${
                    isCurrent
                      ? "apple-glass border-[#0071e3]/40 dark:border-[#0a84ff]/40 shadow-sm"
                      : "bg-white/60 dark:bg-[#1c1c1e]/50 border border-black/[0.05] dark:border-white/[0.06] hover:bg-white dark:hover:bg-[#1c1c1e]"
                  }`}
                >
                  <div className="flex items-center space-x-2.5 mb-2">
                    <div 
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-white"
                      style={{ backgroundColor: card.color }}
                    >
                      <Icon className="w-4 h-4 stroke-[2.2]" />
                    </div>
                    <h3 className="font-semibold text-[14px] text-[#1d1d1f] dark:text-white tracking-tight">
                      {card.title}
                    </h3>
                  </div>

                  <p className="text-[12px] text-[#6e6e73] dark:text-[#a1a1a6] leading-normal line-clamp-2">
                    {card.desc}
                  </p>

                  {isCurrent && (
                    <div 
                      className="absolute bottom-0 left-4 right-4 h-[2px] rounded-full"
                      style={{ backgroundColor: card.color }}
                    />
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Main Module Viewport */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeModule === 1 && <StudentModule />}
        {activeModule === 2 && <TeacherModule />}
        {activeModule === 3 && <TrendsModule />}
        {activeModule === 4 && <MLOpsModule />}
      </main>

      {/* Minimal Footer */}
      <footer className="border-t border-black/[0.06] dark:border-white/[0.08] py-6 px-4 sm:px-6 lg:px-8 text-[12px] text-[#86868b]">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center space-x-2">
            <span className="font-semibold text-[#1d1d1f] dark:text-white">UniAdmit AI</span>
            <span>•</span>
            <span>Đồ Án Dữ Liệu Lớn (IS405.R11)</span>
            <span>•</span>
            <span>Apple Design System</span>
          </div>

          <div className="flex items-center space-x-4 tnum">
            <span>PySpark 4.3.0</span>
            <span>•</span>
            <span>LightGBM Quantile</span>
            <span>•</span>
            <span>Next.js 16</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
