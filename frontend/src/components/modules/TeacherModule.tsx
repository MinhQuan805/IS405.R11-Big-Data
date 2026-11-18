"use client";

import React, { useState, useMemo } from "react";
import mlopsData from "@/data/mlops_meta.json";
import universitiesData from "@/data/universities.json";
import { 
  Users, 
  UploadCloud, 
  BarChart, 
  Scale, 
  FileSpreadsheet, 
  Sparkles, 
  Search,
  CheckCircle2,
  TrendingUp,
  School
} from "lucide-react";
import { 
  ResponsiveContainer, 
  BarChart as RechartsBarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend, 
  LineChart, 
  Line, 
  CartesianGrid,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar
} from "recharts";

export const TeacherModule: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"batch" | "distribution" | "headtohead">("batch");
  const [students, setStudents] = useState<any[]>(mlopsData.class_students || []);
  const [searchStudent, setSearchStudent] = useState<string>("");

  // Head-to-Head selections
  const [compSchool1, setCompSchool1] = useState<string>("BKA");
  const [compSchool2, setCompSchool2] = useState<string>("QHI");
  const [compSchool3, setCompSchool3] = useState<string>("QSB");

  // Ability classification logic
  const classifiedStudents = useMemo(() => {
    return students.map((s) => {
      let ability = "Khá";
      let abilityColor = "text-[#0071e3] bg-[#0071e3]/10";
      if (s.score >= 27.5) {
        ability = "Xuất sắc (Top 2%)";
        abilityColor = "text-[#af52de] bg-[#af52de]/10";
      } else if (s.score >= 25.0) {
        ability = "Giỏi (Top 10%)";
        abilityColor = "text-[#34c759] bg-[#34c759]/10";
      } else if (s.score >= 22.0) {
        ability = "Khá (Top 30%)";
        abilityColor = "text-[#0071e3] bg-[#0071e3]/10";
      } else {
        ability = "Trung bình khá";
        abilityColor = "text-[#ff9500] bg-[#ff9500]/10";
      }

      let suggestions = [];
      if (s.score >= 27.5) {
        suggestions = ["ĐH Bách Khoa HN (Khoa học Máy tính)", "ĐH Ngoại Thương (Kinh tế Đối ngoại)"];
      } else if (s.score >= 25.5) {
        suggestions = ["ĐH Công Nghệ - ĐHQGHN (CNTT)", "ĐH Kinh Tế Quốc Dân (Tài chính - Ngân hàng)"];
      } else if (s.score >= 23.5) {
        suggestions = ["Học Viện BCVT (An toàn thông tin)", "ĐH Thương Mại (Marketing)"];
      } else {
        suggestions = ["ĐH Giao Thông Vận Tải (Cơ điện)", "ĐH Công Nghiệp HN (Điện tử Viễn thông)"];
      }

      // Initials for avatar
      const initials = s.name.split(" ").map((w: string) => w[0]).join("").slice(-2);

      return {
        ...s,
        initials,
        ability,
        abilityColor,
        suggestions
      };
    });
  }, [students]);

  const filteredStudents = useMemo(() => {
    if (!searchStudent) return classifiedStudents;
    return classifiedStudents.filter(
      (s) =>
        s.name.toLowerCase().includes(searchStudent.toLowerCase()) ||
        s.id.toLowerCase().includes(searchStudent.toLowerCase())
    );
  }, [classifiedStudents, searchStudent]);

  const classStats = useMemo(() => {
    if (!students.length) return { avg: 0, median: 0, topTierPct: 0 };
    const scores = students.map((s) => s.score).sort((a, b) => a - b);
    const sum = scores.reduce((acc, curr) => acc + curr, 0);
    const avg = Number((sum / scores.length).toFixed(2));
    const median = scores[Math.floor(scores.length / 2)];
    const topTierCount = scores.filter((s) => s >= 26.0).length;
    const topTierPct = Number(((topTierCount / scores.length) * 100).toFixed(1));
    return { avg, median, topTierPct };
  }, [students]);

  const distributionData = [
    { range: "< 18đ", classPct: 0, nationalPct: 35.2 },
    { range: "18 - 21đ", classPct: 6.7, nationalPct: 32.5 },
    { range: "21 - 24đ", classPct: 13.3, nationalPct: 18.6 },
    { range: "24 - 26đ", classPct: 33.3, nationalPct: 9.4 },
    { range: "26 - 28đ", classPct: 33.3, nationalPct: 3.5 },
    { range: "≥ 28đ", classPct: 13.4, nationalPct: 0.8 },
  ];

  const headToHeadData = [
    { year: "2020", school1: 29.04, school2: 28.10, school3: 27.50 },
    { year: "2021", school1: 28.43, school2: 27.75, school3: 27.20 },
    { year: "2022", school1: 28.29, school2: 28.05, school3: 27.40 },
    { year: "2023", school1: 29.42, school2: 28.15, school3: 27.80 },
    { year: "2024", school1: 29.65, school2: 28.40, school3: 28.00 },
    { year: "2025 (Dự báo)", school1: 29.80, school2: 28.65, school3: 28.20 },
  ];

  const radarComparison = [
    { subject: "Điểm Chuẩn", s1: 98, s2: 92, s3: 90 },
    { subject: "Chỉ Tiêu", s1: 85, s2: 70, s3: 88 },
    { subject: "Google Trends Mùa Tuyển Sinh", s1: 100, s2: 85, s3: 82 },
    { subject: "Độ Cạnh Tranh", s1: 96, s2: 90, s3: 88 },
    { subject: "Việc Làm Sau TN", s1: 95, s2: 94, s3: 93 },
  ];

  const exportBatchReport = () => {
    const header = "Mã HS,Họ Tên,Toán,Lý,Hóa,Văn,Anh,Sinh,Tổ Hợp,Tổng Điểm,Học Lực,Gợi Ý Tuyển Sinh 1,Gợi Ý Tuyển Sinh 2";
    const rows = classifiedStudents.map(
      (s) =>
        `${s.id},"${s.name}",${s.math},${s.phys},${s.chem},${s.lit},${s.eng},${s.bio},${s.block},${s.score},"${s.ability}","${s.suggestions[0]}","${s.suggestions[1] || ""}"`
    );
    const csvContent = "data:text/csv;charset=utf-8,\uFEFF" + [header, ...rows].join("\n");
    const link = document.createElement("a");
    link.href = encodeURI(csvContent);
    link.download = "Bao_Cao_Tu_Van_Lop_12A1.csv";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-8">
      {/* Apple Sub-Navbar Segmented Control */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#1d1d1f] dark:text-white">
            Giáo Viên & Chuyên Viên Tư Vấn
          </h2>
          <p className="text-[14px] text-[#86868b] dark:text-[#a1a1a6] mt-0.5">
            Tư vấn đoàn thể (Batch Counseling), phân tích phổ điểm lớp đối sánh toàn quốc và so sánh đối đầu trường ĐH
          </p>
        </div>

        <div className="apple-segmented-group shadow-sm">
          {[
            { id: "batch", label: "Tư Vấn Hàng Loạt", icon: Users },
            { id: "distribution", label: "Phổ Điểm Lớp", icon: BarChart },
            { id: "headtohead", label: "So Sánh Đối Đầu", icon: Scale },
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
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#5856d6]" : ""}`} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ======================================================== */}
      {/* 2.1 TƯ VẤN HÀNG LOẠT (BATCH COUNSELING) */}
      {/* ======================================================== */}
      {activeTab === "batch" && (
        <div className="space-y-6">
          {/* Action Header Card */}
          <div className="apple-glass p-6 rounded-[28px] flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center space-x-3.5">
              <div className="w-11 h-11 rounded-2xl bg-[#5856d6]/10 text-[#5856d6] flex items-center justify-center border border-[#5856d6]/20 shadow-sm">
                <Users className="w-5 h-5 stroke-[2.2]" />
              </div>
              <div>
                <h4 className="font-bold text-[16px] text-[#1d1d1f] dark:text-white">
                  Danh Sách Điểm Lớp 12A1 ({students.length} Học Sinh)
                </h4>
                <p className="text-[12px] text-[#86868b]">
                  Dữ liệu điểm thi đã sẵn sàng phân loại và tự động gợi ý trường phù hợp
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={exportBatchReport}
                className="py-2.5 px-5 apple-button-primary flex items-center space-x-2 text-[13px]"
              >
                <FileSpreadsheet className="w-4 h-4" />
                <span>Xuất Báo Cáo Tư Vấn (Excel)</span>
              </button>
            </div>
          </div>

          {/* Student Roster Table */}
          <div className="apple-glass p-6 rounded-[28px] space-y-4">
            <div className="flex items-center justify-between">
              <div className="relative w-72">
                <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#86868b]" />
                <input
                  type="text"
                  placeholder="Tìm học sinh theo tên..."
                  value={searchStudent}
                  onChange={(e) => setSearchStudent(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-[13px] rounded-full bg-black/[0.04] dark:bg-white/[0.08] border border-black/[0.06] dark:border-white/[0.08] text-[#1d1d1f] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#5856d6]"
                />
              </div>
              <span className="text-[12px] text-[#86868b]">
                Hiển thị {filteredStudents.length} / {students.length} em
              </span>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="border-b border-black/[0.06] dark:border-white/[0.08] text-[#86868b] font-semibold text-[11px] uppercase tracking-wider">
                    <th className="py-3 px-3">Học Sinh</th>
                    <th className="py-3 px-3 text-center">Khối</th>
                    <th className="py-3 px-3 text-center">Điểm Tổ Hợp</th>
                    <th className="py-3 px-3 text-center">Học Lực</th>
                    <th className="py-3 px-3">Mục Tiêu Ban Đầu</th>
                    <th className="py-3 px-3">AI Gợi Ý Phù Hợp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/[0.04] dark:divide-white/[0.04]">
                  {filteredStudents.map((s) => (
                    <tr key={s.id} className="hover:bg-black/[0.02] dark:hover:bg-white/[0.03] transition-colors">
                      <td className="py-3 px-3">
                        <div className="flex items-center space-x-2.5">
                          <span className="w-7 h-7 rounded-full bg-[#5856d6]/10 text-[#5856d6] font-bold text-[11px] flex items-center justify-center">
                            {s.initials}
                          </span>
                          <div>
                            <span className="font-semibold text-[#1d1d1f] dark:text-white block">{s.name}</span>
                            <span className="text-[10px] text-[#86868b] font-mono">{s.id}</span>
                          </div>
                        </div>
                      </td>
                      <td className="py-3 px-3 text-center font-mono text-[12px] text-[#86868b]">
                        {s.block}
                      </td>
                      <td className="py-3 px-3 text-center font-extrabold text-[#1d1d1f] dark:text-white">
                        {s.score}đ
                      </td>
                      <td className="py-3 px-3 text-center">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${s.abilityColor}`}>
                          {s.ability}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-[#86868b] text-[12px]">
                        {s.target}
                      </td>
                      <td className="py-3 px-3">
                        <div className="space-y-1">
                          {s.suggestions.map((sug: string, i: number) => (
                            <span
                              key={i}
                              className="inline-block px-2.5 py-0.5 rounded-lg text-[11px] bg-black/[0.03] dark:bg-white/[0.06] text-[#1d1d1f] dark:text-white mr-1.5"
                            >
                              ✓ {sug}
                            </span>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 2.2 BÁO CÁO PHÂN TÍCH PHỔ ĐIỂM LỚP */}
      {/* ======================================================== */}
      {activeTab === "distribution" && (
        <div className="space-y-6">
          {/* Apple Stat Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="apple-glass p-6 rounded-[28px] space-y-1">
              <span className="text-[12px] text-[#86868b] font-medium block">Điểm Trung Bình Lớp</span>
              <div className="text-3xl font-extrabold text-[#5856d6]">{classStats.avg} điểm</div>
              <span className="text-[12px] text-[#34c759] font-medium block">
                +{(classStats.avg - 19.45).toFixed(2)}đ so với toàn quốc (19.45đ)
              </span>
            </div>

            <div className="apple-glass p-6 rounded-[28px] space-y-1">
              <span className="text-[12px] text-[#86868b] font-medium block">Điểm Trung Vị (Median)</span>
              <div className="text-3xl font-extrabold text-[#1d1d1f] dark:text-white">{classStats.median} điểm</div>
              <span className="text-[12px] text-[#86868b] block">50% học sinh đạt mức này trở lên</span>
            </div>

            <div className="apple-glass p-6 rounded-[28px] space-y-1">
              <span className="text-[12px] text-[#86868b] font-medium block">Tỷ Lệ Điểm Top Tier (≥ 26đ)</span>
              <div className="text-3xl font-extrabold text-[#af52de]">{classStats.topTierPct}%</div>
              <span className="text-[12px] text-[#86868b] block">Toàn quốc chỉ đạt xấp xỉ 4.3%</span>
            </div>
          </div>

          {/* Histogram Comparison Bar Chart */}
          <div className="apple-glass p-7 rounded-[32px] space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white">
                  Phổ Điểm Lớp 12A1 Đối Soát Chuẩn Quốc Gia
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  Đánh giá phân bố năng lực thực tế để hỗ trợ phân luồng nguyện vọng
                </p>
              </div>
              <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-[#34c759]/10 text-[#34c759] border border-[#34c759]/20">
                Hiệu Suất Tuyển Sinh Cao
              </span>
            </div>

            <div className="h-80 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsBarChart data={distributionData} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.12} />
                  <XAxis dataKey="range" tick={{ fontSize: 11 }} stroke="#86868b" />
                  <YAxis tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} stroke="#86868b" />
                  <Tooltip 
                    formatter={(val: any) => [`${val}%`, ""]}
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.85)",
                      backdropFilter: "blur(20px)",
                      borderRadius: "16px",
                      border: "1px solid rgba(0, 0, 0, 0.08)"
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
                  <Bar dataKey="classPct" name="Lớp 12A1 (%)" fill="#5856d6" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="nationalPct" name="Phổ Điểm Toàn Quốc (%)" fill="#a1a1a6" radius={[8, 8, 0, 0]} />
                </RechartsBarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 2.3 SO SÁNH ĐỐI ĐẦU GIỮA CÁC TRƯỜNG / NGÀNH (HEAD-TO-HEAD) */}
      {/* ======================================================== */}
      {activeTab === "headtohead" && (
        <div className="space-y-6">
          {/* Apple Compare Selector */}
          <div className="apple-glass p-6 rounded-[28px] space-y-4">
            <h3 className="font-bold text-[15px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
              <Scale className="w-4 h-4 text-[#5856d6]" />
              <span>Đặt 2 – 3 Trường Lên Bàn Cân So Sánh</span>
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                { label: "Trường A (Xanh Dương)", val: compSchool1, set: setCompSchool1, color: "#0071e3" },
                { label: "Trường B (Tím)", val: compSchool2, set: setCompSchool2, color: "#af52de" },
                { label: "Trường C (Xanh Ngọc)", val: compSchool3, set: setCompSchool3, color: "#34c759" },
              ].map((item, idx) => (
                <div key={idx} className="space-y-1">
                  <label className="text-[11px] font-semibold block" style={{ color: item.color }}>
                    {item.label}
                  </label>
                  <select
                    value={item.val}
                    onChange={(e) => item.set(e.target.value)}
                    className="w-full px-3.5 py-2.5 text-[13px] rounded-2xl bg-black/[0.03] dark:bg-white/[0.06] border border-black/[0.06] dark:border-white/[0.08] font-medium focus:outline-none focus:ring-2 focus:ring-[#5856d6]"
                  >
                    {(universitiesData as any[]).map((u) => (
                      <option key={u.school_id} value={u.school_id} className="dark:bg-[#1c1c1e]">
                        [{u.school_id}] {u.school_name}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>

          {/* Side-by-side charts */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            <div className="lg:col-span-7 apple-glass p-6 rounded-[28px] space-y-4">
              <h4 className="font-bold text-[15px] text-[#1d1d1f] dark:text-white">
                Diễn Biến Điểm Chuẩn 5 Năm (2020 - 2025)
              </h4>
              <div className="h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={headToHeadData} margin={{ top: 10, right: 30, left: -10, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" opacity={0.12} />
                    <XAxis dataKey="year" tick={{ fontSize: 11 }} stroke="#86868b" />
                    <YAxis domain={[26.5, 30.2]} tick={{ fontSize: 11 }} stroke="#86868b" />
                    <Tooltip 
                      formatter={(val: any) => [`${val} điểm`, ""]}
                      contentStyle={{
                        backgroundColor: "rgba(255, 255, 255, 0.85)",
                        backdropFilter: "blur(20px)",
                        borderRadius: "16px",
                        border: "1px solid rgba(0, 0, 0, 0.08)"
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "11px" }} />
                    <Line type="monotone" dataKey="school1" name={compSchool1} stroke="#0071e3" strokeWidth={3} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="school2" name={compSchool2} stroke="#af52de" strokeWidth={3} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="school3" name={compSchool3} stroke="#34c759" strokeWidth={3} dot={{ r: 4 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="lg:col-span-5 apple-glass p-6 rounded-[28px] space-y-4">
              <h4 className="font-bold text-[15px] text-[#1d1d1f] dark:text-white">
                Đối Soát Đa Tiêu Chí Tuyển Sinh
              </h4>
              <div className="h-72 w-full flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarComparison}>
                    <PolarGrid opacity={0.2} />
                    <PolarAngleAxis dataKey="subject" tick={{ fontSize: 9 }} />
                    <Radar name={compSchool1} dataKey="s1" stroke="#0071e3" fill="#0071e3" fillOpacity={0.25} />
                    <Radar name={compSchool2} dataKey="s2" stroke="#af52de" fill="#af52de" fillOpacity={0.25} />
                    <Radar name={compSchool3} dataKey="s3" stroke="#34c759" fill="#34c759" fillOpacity={0.25} />
                    <Legend wrapperStyle={{ fontSize: "11px" }} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
