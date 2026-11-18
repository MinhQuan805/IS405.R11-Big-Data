"use client";

import React from "react";
import { 
  GraduationCap, 
  Users, 
  TrendingUp, 
  Cpu, 
  Moon, 
  Sun,
  Compass
} from "lucide-react";

interface AppleNavbarProps {
  activeModule: number;
  setActiveModule: (id: number) => void;
  isDark: boolean;
  toggleDark: () => void;
}

export const AppleNavbar: React.FC<AppleNavbarProps> = ({
  activeModule,
  setActiveModule,
  isDark,
  toggleDark,
}) => {
  const modules = [
    { id: 1, label: "Thí Sinh", icon: GraduationCap },
    { id: 2, label: "Giáo Viên", icon: Users },
    { id: 3, label: "Google Trends", icon: TrendingUp },
    { id: 4, label: "MLOps", icon: Cpu },
  ];

  return (
    <header className="sticky top-0 z-50 w-full apple-nav transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-14">
          {/* Logo - Minimal & Sharp */}
          <div 
            className="flex items-center space-x-2.5 cursor-pointer select-none" 
            onClick={() => setActiveModule(1)}
          >
            <div className="w-8 h-8 rounded-xl bg-[#0071e3] dark:bg-[#0a84ff] flex items-center justify-center text-white shadow-sm">
              <Compass className="w-4 h-4 stroke-[2.4]" />
            </div>
            
            <div className="flex items-baseline space-x-1.5">
              <span className="font-semibold text-[15px] tracking-tight text-[#1d1d1f] dark:text-white">
                UniAdmit
              </span>
              <span className="text-[10px] font-bold tracking-wider uppercase text-[#86868b]">
                v3.0
              </span>
            </div>
          </div>

          {/* Genuine Apple Segmented Switcher */}
          <nav className="hidden md:flex apple-segmented-track">
            {modules.map((m) => {
              const Icon = m.icon;
              const isActive = activeModule === m.id;
              return (
                <button
                  key={m.id}
                  onClick={() => setActiveModule(m.id)}
                  className={`apple-segmented-btn flex items-center space-x-1.5 ${
                    isActive ? "apple-segmented-btn-active" : ""
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#0071e3] dark:text-[#0a84ff]" : ""}`} />
                  <span>{m.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Right Status Indicator & Theme Toggle */}
          <div className="flex items-center space-x-3">
            {/* Live Serving Status */}
            <div className="hidden sm:flex items-center space-x-2 text-[12px] text-[#6e6e73] dark:text-[#a1a1a6]">
              <span className="w-2 h-2 rounded-full bg-[#34c759]" />
              <span className="tnum font-medium">Spark 4.3 • 15.8ms</span>
            </div>

            <div className="h-4 w-px bg-black/[0.08] dark:bg-white/[0.1] hidden sm:block" />

            {/* Dark / Light Toggle */}
            <button
              onClick={toggleDark}
              aria-label="Chuyển giao diện sáng/tối"
              className="w-8 h-8 rounded-full flex items-center justify-center bg-black/[0.04] dark:bg-white/[0.08] hover:bg-black/[0.08] dark:hover:bg-white/[0.14] text-[#1d1d1f] dark:text-[#f5f5f7] transition-colors"
            >
              {isDark ? (
                <Sun className="w-3.5 h-3.5 text-[#ff9f0a]" />
              ) : (
                <Moon className="w-3.5 h-3.5 text-[#1d1d1f]" />
              )}
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        <div className="md:hidden flex items-center space-x-1 pb-2.5 overflow-x-auto no-scrollbar">
          {modules.map((m) => {
            const Icon = m.icon;
            const isActive = activeModule === m.id;
            return (
              <button
                key={m.id}
                onClick={() => setActiveModule(m.id)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-full text-xs whitespace-nowrap transition-all ${
                  isActive
                    ? "bg-[#0071e3] text-white font-medium shadow-sm"
                    : "bg-black/[0.04] dark:bg-white/[0.08] text-[#6e6e73]"
                }`}
              >
                <Icon className="w-3 h-3" />
                <span>{m.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
};
