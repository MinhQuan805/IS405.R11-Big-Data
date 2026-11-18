"use client";

import React, { useState } from "react";
import googleTrendsData from "@/data/google_trends.json";
import { 
  TrendingUp, 
  Flame, 
  MapPin, 
  LineChart as LineChartIcon, 
  Calendar, 
  Sparkles,
  Zap
} from "lucide-react";
import { 
  ResponsiveContainer, 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  CartesianGrid, 
  Bar, 
  ComposedChart
} from "recharts";

export const TrendsModule: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"seasonal" | "hotness" | "geo" | "correlation">("seasonal");
  const [selectedEntity, setSelectedEntity] = useState<"schools" | "industries">("schools");

  const { seasonal_radar, industry_hotness, geo_provinces, trends_vs_cutoff } = googleTrendsData;

  return (
    <div className="space-y-8">
      {/* Apple Sub-Navbar Segmented Control */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#1d1d1f] dark:text-white">
            Google Trends & Dữ Liệu Lớn Tuyển Sinh
          </h2>
          <p className="text-[14px] text-[#86868b] dark:text-[#a1a1a6] mt-0.5">
            Nhịp mùa thi 12 tháng, xếp hạng độ nóng ngành học và chứng minh mối quan hệ giữa xu hướng tìm kiếm vs điểm chuẩn
          </p>
        </div>

        <div className="apple-segmented-group shadow-sm">
          {[
            { id: "seasonal", label: "Nhịp Mùa Thi", icon: Calendar },
            { id: "hotness", label: "Độ Nóng Ngành/Trường", icon: Flame },
            { id: "geo", label: "Bản Đồ Tỉnh Thành", icon: MapPin },
            { id: "correlation", label: "Tương Quan Điểm Chuẩn", icon: LineChartIcon },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-1.5 px-4 py-1.5 apple-segmented-item ${
                  isActive ? "apple-segmented-item-active" : "text-[#86868b]"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#ff9500]" : ""}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ======================================================== */}
      {/* 3.1 RADAR NHỊP MÙA THI (SEASONAL TRENDS) */}
      {/* ======================================================== */}
      {activeTab === "seasonal" && (
        <div className="space-y-6">
          <div className="apple-glass p-7 rounded-[32px] space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <Calendar className="w-5 h-5 text-[#ff9500]" />
                  <span>Chu Kỳ Quan Tâm Xã Hội Tuyển Sinh (Seasonal Pulse)</span>
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  Chuỗi thời gian thể hiện đỉnh nhọn tìm kiếm bùng nổ vào mùa thi (Tháng 6 - Tháng 8)
                </p>
              </div>

              {/* Entity switcher */}
              <div className="apple-segmented-group">
                <button
                  onClick={() => setSelectedEntity("schools")}
                  className={`px-3 py-1 apple-segmented-item ${
                    selectedEntity === "schools" ? "apple-segmented-item-active" : "text-[#86868b]"
                  }`}
                >
                  Các Trường Đại Học
                </button>
                <button
                  onClick={() => setSelectedEntity("industries")}
                  className={`px-3 py-1 apple-segmented-item ${
                    selectedEntity === "industries" ? "apple-segmented-item-active" : "text-[#86868b]"
                  }`}
                >
                  Khối Ngành Trọng Điểm
                </button>
              </div>
            </div>

            <div className="h-80 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={seasonal_radar} margin={{ top: 10, right: 30, left: -10, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.12} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} stroke="#86868b" />
                  <YAxis domain={[0, 105]} tick={{ fontSize: 11 }} stroke="#86868b" />
                  <Tooltip 
                    formatter={(val: any) => [`${val}/100`, "Chỉ số Trends"]}
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.85)",
                      backdropFilter: "blur(20px)",
                      borderRadius: "16px",
                      border: "1px solid rgba(0, 0, 0, 0.08)"
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  {selectedEntity === "schools" ? (
                    <>
                      <Line type="monotone" dataKey="BKA" name="ĐH Bách Khoa HN" stroke="#ff3b30" strokeWidth={3} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="KHA" name="ĐH Kinh Tế Quốc Dân" stroke="#0071e3" strokeWidth={3} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="NTH" name="ĐH Ngoại Thương" stroke="#34c759" strokeWidth={3} dot={{ r: 3 }} />
                      <Line type="monotone" dataKey="QHI" name="ĐH Công Nghệ ĐHQGHN" stroke="#af52de" strokeWidth={3} dot={{ r: 3 }} />
                    </>
                  ) : (
                    <>
                      <Line type="monotone" dataKey="industry_cntt" name="Công Nghệ Thông Tin" stroke="#0071e3" strokeWidth={3.5} dot={{ r: 4 }} />
                      <Line type="monotone" dataKey="industry_semiconductor" name="Thiết Kế Vi Mạch & Bán Dẫn" stroke="#ff9500" strokeWidth={3.5} dot={{ r: 4 }} />
                    </>
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="p-4 rounded-2xl bg-[#ff9500]/10 border border-[#ff9500]/20 flex items-start space-x-2.5">
              <Sparkles className="w-4 h-4 text-[#ff9500] shrink-0 mt-0.5" />
              <p className="text-[13px] text-[#ff9500] dark:text-[#ff9f0a] leading-relaxed">
                <strong>Phát hiện Big Data:</strong> Vào tháng 6 và tháng 7 hàng năm, mức độ tìm kiếm trực tuyến tăng vọt 300% tạo thành đỉnh nhọn đặc trưng. Khối ngành Vi mạch & Bán dẫn có tốc độ tăng trưởng thảo luận xã hội cao kỷ lục (+142.6% YoY).
              </p>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 3.2 SO SÁNH ĐỘ "NÓNG" GIỮA CÁC TRƯỜNG/NGÀNH */}
      {/* ======================================================== */}
      {activeTab === "hotness" && (
        <div className="space-y-6">
          <div className="apple-glass p-7 rounded-[32px] space-y-6">
            <div className="flex items-center justify-between pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <Flame className="w-5 h-5 text-[#ff3b30]" />
                  <span>Xếp Hạng Sức Hút Tìm Kiếm & Xu Hướng Tăng Trưởng</span>
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  So sánh mức độ tìm kiếm trực tuyến các khối ngành chiến lược quốc gia
                </p>
              </div>
              <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-[#ff3b30]/10 text-[#ff3b30] border border-[#ff3b30]/20 flex items-center space-x-1">
                <Zap className="w-3.5 h-3.5" />
                <span>Real-Time Trends</span>
              </span>
            </div>

            {/* Apple App Store Style Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {industry_hotness.map((ind, i) => (
                <div 
                  key={i} 
                  className="p-5 rounded-[24px] bg-black/[0.02] dark:bg-white/[0.04] border border-black/[0.05] dark:border-white/[0.07] apple-card-interactive space-y-3.5"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[15px] text-[#1d1d1f] dark:text-white">
                      {ind.industry}
                    </span>
                    <span className="text-[12px] font-extrabold text-[#34c759]">
                      {ind.growth_yoy}
                    </span>
                  </div>

                  <div className="space-y-1.5">
                    <div className="flex justify-between text-[12px] text-[#86868b]">
                      <span>Độ nóng Google Trends</span>
                      <strong className="text-[#1d1d1f] dark:text-white">{ind.search_volume}/100</strong>
                    </div>
                    <div className="w-full h-2.5 bg-black/[0.06] dark:bg-white/[0.08] rounded-full overflow-hidden">
                      <div 
                        className="h-full rounded-full bg-gradient-to-r from-[#ff9500] to-[#ff3b30]" 
                        style={{ width: `${ind.search_volume}%` }} 
                      />
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-1 text-[12px] text-[#86868b]">
                    <span>Điểm chuẩn đỉnh: <strong>{ind.peak_score}đ</strong></span>
                    <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-black/[0.04] dark:bg-white/[0.08] text-[#1d1d1f] dark:text-white">
                      {ind.heat_level}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 3.3 BẢN ĐỒ QUAN TÂM THEO TỈNH THÀNH (GEO TRENDS) */}
      {/* ======================================================== */}
      {activeTab === "geo" && (
        <div className="space-y-6">
          <div className="apple-glass p-7 rounded-[32px] space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <MapPin className="w-5 h-5 text-[#0071e3]" />
                  <span>Mật Độ Quan Tâm Tuyển Sinh Theo Tỉnh Thành</span>
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  Dữ liệu phân tích địa lý thí sinh tìm kiếm nhiều nhất về các trường ĐH
                </p>
              </div>

              <div className="flex items-center space-x-2 text-[12px] text-[#86868b]">
                <span className="w-2.5 h-2.5 rounded-full bg-[#0071e3]" />
                <span>Mật độ cao</span>
                <span className="w-2.5 h-2.5 rounded-full bg-[#0071e3]/30 ml-2" />
                <span>Mật độ vừa</span>
              </div>
            </div>

            {/* Apple Map Province Tiles */}
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
              {geo_provinces.map((prov, idx) => (
                <div 
                  key={idx}
                  className="p-4 rounded-[22px] border transition-all apple-card-interactive"
                  style={{
                    backgroundColor: `rgba(0, 113, 227, ${prov.search_intensity / 450 + 0.04})`,
                    borderColor: `rgba(0, 113, 227, ${prov.search_intensity / 240})`
                  }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-[13px] text-[#1d1d1f] dark:text-white">
                      {prov.province}
                    </span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded font-mono font-bold bg-white/80 dark:bg-black/60 text-[#0071e3]">
                      {prov.code}
                    </span>
                  </div>
                  <div className="text-2xl font-extrabold text-[#0071e3] dark:text-[#0a84ff]">
                    {prov.search_intensity}
                  </div>
                  <div className="text-[11px] text-[#86868b] flex justify-between mt-1">
                    <span>{prov.region}</span>
                    <span>~{(prov.candidates / 1000).toFixed(0)}k thí sinh</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 3.4 TƯƠNG QUAN GOOGLE TRENDS VS ĐIỂM CHUẨN */}
      {/* ======================================================== */}
      {activeTab === "correlation" && (
        <div className="space-y-6">
          <div className="apple-glass p-7 rounded-[32px] space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <LineChartIcon className="w-5 h-5 text-[#34c759]" />
                  <span>Mô Hình Đường Kép: Tương Quan Google Trends & Điểm Chuẩn</span>
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  Chứng minh thực nghiệm: Mức độ quan tâm trong năm t-1 thúc đẩy điểm chuẩn năm sau tăng
                </p>
              </div>

              <div className="px-3.5 py-1.5 rounded-full bg-[#34c759]/10 text-[#248a3d] dark:text-[#30d158] border border-[#34c759]/20 text-[12px] font-bold">
                Hệ số tương quan r = 0.93 (Rất mạnh)
              </div>
            </div>

            <div className="h-80 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={trends_vs_cutoff} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.12} />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} stroke="#86868b" />
                  <YAxis 
                    yAxisId="left" 
                    orientation="left" 
                    domain={[60, 110]} 
                    tick={{ fontSize: 11 }} 
                    stroke="#ff9500"
                    label={{ value: "Trends Index", angle: -90, position: "insideLeft", fontSize: 10, fill: "#ff9500" }}
                  />
                  <YAxis 
                    yAxisId="right" 
                    orientation="right" 
                    domain={[26, 30.5]} 
                    tick={{ fontSize: 11 }} 
                    stroke="#0071e3"
                    label={{ value: "Điểm chuẩn (BKA)", angle: 90, position: "insideRight", fontSize: 10, fill: "#0071e3" }}
                  />
                  <Tooltip 
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.85)",
                      backdropFilter: "blur(20px)",
                      borderRadius: "16px",
                      border: "1px solid rgba(0, 0, 0, 0.08)"
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  <Bar yAxisId="left" dataKey="trend_index" name="Google Trends Index (t-1)" fill="#ff9500" radius={[6, 6, 0, 0]} opacity={0.65} />
                  <Line yAxisId="right" type="monotone" dataKey="cutoff_bka_cntt" name="Điểm chuẩn BKA - CNTT" stroke="#0071e3" strokeWidth={3} dot={{ r: 4 }} />
                  <Line yAxisId="right" type="monotone" dataKey="cutoff_kha_kinhte" name="Điểm chuẩn NEU - Kinh Tế" stroke="#af52de" strokeWidth={3} strokeDasharray="4 4" dot={{ r: 4 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
