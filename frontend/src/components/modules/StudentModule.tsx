"use client";

import React, { useState, useMemo } from "react";
import universitiesData from "@/data/universities.json";
import programsData from "@/data/programs.json";
import cdfDataRaw from "@/data/cdf_data.json";
import { 
  calculateAdmissionProbability, 
  getDecisionTier, 
  classifyWishlistCategory, 
  analyzeWishlistStrategy,
  WishlistItem
} from "@/lib/admission-engine";
import { 
  Target, 
  Sliders, 
  BookmarkPlus, 
  Trash2, 
  Sparkles, 
  CheckCircle2, 
  AlertTriangle, 
  TrendingUp, 
  FileSpreadsheet, 
  FileText, 
  ArrowUpDown, 
  BarChart2,
  ChevronRight,
  ShieldCheck,
  Percent,
  Search,
  School,
  ArrowUp,
  ArrowDown,
  Printer
} from "lucide-react";
import confetti from "canvas-confetti";
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  Tooltip, 
  ReferenceLine
} from "recharts";

interface ProgramItem {
  school_id: string;
  school_name: string;
  score_code: string;
  score_name: string;
  score_blocks: string[];
  latest_score: number;
  latest_year: number;
  history: Record<string, number>;
  quota?: number;
  quantile_10?: number;
  quantile_50?: number;
  quantile_90?: number;
  volatility?: number;
}

export const StudentModule: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"predict" | "wishlist" | "whatif" | "recommend" | "cdf" | "export">("predict");

  // Inputs for 1.1 Predictor
  const [selectedBlock, setSelectedBlock] = useState<string>("A00");
  const [sub1, setSub1] = useState<number>(9.0);
  const [sub2, setSub2] = useState<number>(8.5);
  const [sub3, setSub3] = useState<number>(8.5);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>("BKA");
  const [selectedProgramCode, setSelectedProgramCode] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // What-If delta adjustments
  const [whatIfDelta1, setWhatIfDelta1] = useState<number>(0.0);
  const [whatIfDelta2, setWhatIfDelta2] = useState<number>(0.0);
  const [whatIfDelta3, setWhatIfDelta3] = useState<number>(0.0);

  // Smart Wishlist state
  const [wishlist, setWishlist] = useState<WishlistItem[]>([
    {
      id: "w1",
      order: 1,
      schoolId: "BKA",
      schoolName: "Đại Học Bách Khoa Hà Nội",
      majorCode: "IT1",
      majorName: "Khoa học Máy tính (IT1)",
      block: "A00",
      cutoffScore: 29.42,
      userScore: 26.0,
      probability: 0.38,
      tier: "risky",
      category: "dream"
    },
    {
      id: "w2",
      order: 2,
      schoolId: "QHI",
      schoolName: "Trường Đại Học Công Nghệ – ĐHQGHN",
      majorCode: "CN1",
      majorName: "Công nghệ Thông tin",
      block: "A00",
      cutoffScore: 27.80,
      userScore: 26.0,
      probability: 0.74,
      tier: "competitive",
      category: "target"
    },
    {
      id: "w3",
      order: 3,
      schoolId: "BVH",
      schoolName: "Học Viện Công Nghệ Bưu Chính Viễn Thông",
      majorCode: "7480201",
      majorName: "Công nghệ Thông tin",
      block: "A00",
      cutoffScore: 26.15,
      userScore: 26.0,
      probability: 0.81,
      tier: "competitive",
      category: "target"
    },
    {
      id: "w4",
      order: 4,
      schoolId: "GHA",
      schoolName: "Trường Đại Học Giao Thông Vận Tải",
      majorCode: "7480201",
      majorName: "Công nghệ Thông tin",
      block: "A00",
      cutoffScore: 24.30,
      userScore: 26.0,
      probability: 0.94,
      tier: "safe",
      category: "safety"
    }
  ]);

  // Available programs for current school
  const schoolPrograms = useMemo(() => {
    return (programsData as unknown as ProgramItem[]).filter(
      (p) => p.school_id === selectedSchoolId
    );
  }, [selectedSchoolId]);

  // Current selected program
  const currentProgram = useMemo(() => {
    if (selectedProgramCode) {
      const found = schoolPrograms.find((p) => p.score_code === selectedProgramCode);
      if (found) return found;
    }
    return schoolPrograms[0] || (programsData as unknown as ProgramItem[])[0];
  }, [selectedProgramCode, schoolPrograms]);

  // Block subject names
  const subjectNames = useMemo(() => {
    switch (selectedBlock) {
      case "A00": return { s1: "Toán", s2: "Vật lí", s3: "Hóa học" };
      case "A01": return { s1: "Toán", s2: "Vật lí", s3: "Tiếng Anh" };
      case "B00": return { s1: "Toán", s2: "Hóa học", s3: "Sinh học" };
      case "C00": return { s1: "Ngữ văn", s2: "Lịch sử", s3: "Địa lí" };
      case "D01": return { s1: "Toán", s2: "Ngữ văn", s3: "Tiếng Anh" };
      case "D07": return { s1: "Toán", s2: "Hóa học", s3: "Tiếng Anh" };
      default: return { s1: "Môn 1", s2: "Môn 2", s3: "Môn 3" };
    }
  }, [selectedBlock]);

  // Scores
  const totalBaseScore = useMemo(() => {
    return Math.min(30, Math.max(0, Number((sub1 + sub2 + sub3).toFixed(2))));
  }, [sub1, sub2, sub3]);

  const totalWhatIfScore = useMemo(() => {
    const s1 = Math.min(10, Math.max(0, sub1 + whatIfDelta1));
    const s2 = Math.min(10, Math.max(0, sub2 + whatIfDelta2));
    const s3 = Math.min(10, Math.max(0, sub3 + whatIfDelta3));
    return Math.min(30, Math.max(0, Number((s1 + s2 + s3).toFixed(2))));
  }, [sub1, sub2, sub3, whatIfDelta1, whatIfDelta2, whatIfDelta3]);

  // CDF lookup
  const cdfList = useMemo(() => {
    return (cdfDataRaw as Record<string, any[]>)[selectedBlock] || [];
  }, [selectedBlock]);

  const lookupRankPercentile = (score: number) => {
    if (!cdfList.length) return 0.5;
    let closest = cdfList[0];
    let minDiff = 999;
    for (const pt of cdfList) {
      const diff = Math.abs(pt.score - score);
      if (diff < minDiff) {
        minDiff = diff;
        closest = pt;
      }
    }
    return closest.rank_pct_gt;
  };

  // Prediction computation
  const predictionResult = useMemo(() => {
    if (!currentProgram) return null;
    const studentRank = lookupRankPercentile(totalBaseScore);
    const cutoffScore = currentProgram.latest_score || 24.5;
    const cutoffRank = lookupRankPercentile(cutoffScore);

    const q10 = Number((cutoffScore - 1.15).toFixed(2));
    const q50 = cutoffScore;
    const q90 = Number((cutoffScore + 1.25).toFixed(2));

    const scoreDiff = totalBaseScore - cutoffScore;
    const rawProb = 1 / (1 + Math.exp(-1.35 * scoreDiff));
    const probability = Math.min(0.99, Math.max(0.02, rawProb));
    const tier = getDecisionTier(probability);

    return {
      score: totalBaseScore,
      studentRank,
      cutoffRank,
      cutoffScore,
      q10,
      q50,
      q90,
      probability,
      tier
    };
  }, [totalBaseScore, currentProgram, cdfList]);

  // What-If computation
  const whatIfResult = useMemo(() => {
    if (!currentProgram) return null;
    const cutoffScore = currentProgram.latest_score || 24.5;
    const scoreDiff = totalWhatIfScore - cutoffScore;
    const rawProb = 1 / (1 + Math.exp(-1.35 * scoreDiff));
    const probability = Math.min(0.99, Math.max(0.02, rawProb));
    const tier = getDecisionTier(probability);
    const probDelta = probability - (predictionResult?.probability || 0);

    return {
      score: totalWhatIfScore,
      probability,
      tier,
      probDelta
    };
  }, [totalWhatIfScore, currentProgram, predictionResult]);

  // Wishlist actions
  const addToWishlist = (program: ProgramItem, customProb?: number) => {
    const prob = customProb !== undefined ? customProb : (predictionResult?.probability || 0.5);
    const cat = classifyWishlistCategory(prob);
    const tier = getDecisionTier(prob).tier;

    const newItem: WishlistItem = {
      id: `wish-${Date.now()}`,
      order: wishlist.length + 1,
      schoolId: program.school_id,
      schoolName: program.school_name,
      majorCode: program.score_code,
      majorName: program.score_name,
      block: selectedBlock,
      cutoffScore: program.latest_score,
      userScore: totalBaseScore,
      probability: prob,
      tier,
      category: cat
    };

    setWishlist([...wishlist, newItem]);
    if (prob >= 0.85) {
      confetti({ particleCount: 50, spread: 60, origin: { y: 0.7 } });
    }
  };

  const removeFromWishlist = (id: string) => {
    setWishlist(wishlist.filter((w) => w.id !== id).map((w, idx) => ({ ...w, order: idx + 1 })));
  };

  const moveOrder = (index: number, direction: "up" | "down") => {
    if ((direction === "up" && index === 0) || (direction === "down" && index === wishlist.length - 1)) return;
    const targetIdx = direction === "up" ? index - 1 : index + 1;
    const clone = [...wishlist];
    const temp = clone[index];
    clone[index] = clone[targetIdx];
    clone[targetIdx] = temp;
    setWishlist(clone.map((item, idx) => ({ ...item, order: idx + 1 })));
  };

  const strategyAnalysis = useMemo(() => analyzeWishlistStrategy(wishlist), [wishlist]);

  // Filtered recommended programs
  const recommendedPrograms = useMemo(() => {
    return (programsData as unknown as ProgramItem[])
      .filter((p) => {
        if (!p.score_blocks.includes(selectedBlock)) return false;
        if (searchQuery && !p.school_name.toLowerCase().includes(searchQuery.toLowerCase()) && !p.score_name.toLowerCase().includes(searchQuery.toLowerCase())) {
          return false;
        }
        const diff = totalBaseScore - p.latest_score;
        const prob = 1 / (1 + Math.exp(-1.35 * diff));
        return prob >= 0.70;
      })
      .slice(0, 30);
  }, [totalBaseScore, selectedBlock, searchQuery]);

  // Circular gauge circumference
  const radius = 54;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (predictionResult?.probability || 0.5) * circumference;

  return (
    <div className="space-y-8">
      {/* Apple Sub-Navbar Segmented Control */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-[#1d1d1f] dark:text-white">
            Thí Sinh & Xét Tuyển Cá Nhân Hóa
          </h2>
          <p className="text-[14px] text-[#86868b] dark:text-[#a1a1a6] mt-0.5">
            Dự báo xác suất trúng tuyển, thiết kế giỏ nguyện vọng và kiểm tra độ nhạy điểm số
          </p>
        </div>

        {/* Apple Segmented Bar */}
        <div className="apple-segmented-group shadow-sm overflow-x-auto no-scrollbar">
          {[
            { id: "predict", label: "Dự Báo", icon: Target },
            { id: "wishlist", label: "Giỏ NV Smart", icon: BookmarkPlus },
            { id: "whatif", label: "Mô Phỏng What-If", icon: Sliders },
            { id: "recommend", label: "Gợi Ý Ngành", icon: Sparkles },
            { id: "cdf", label: "Vị Thế CDF", icon: BarChart2 },
            { id: "export", label: "Phiếu NV", icon: FileText },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`flex items-center space-x-1.5 px-3.5 py-1.5 apple-segmented-item ${
                  isActive
                    ? "apple-segmented-item-active"
                    : "text-[#86868b] hover:text-[#1d1d1f] dark:text-[#a1a1a6] dark:hover:text-white"
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? "text-[#0071e3] dark:text-[#0a84ff]" : ""}`} />
                <span className="whitespace-nowrap">{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* ======================================================== */}
      {/* 1.1 DỰ BÁO XÁC SUẤT TRÚNG TUYỂN LIÊN TỤC */}
      {/* ======================================================== */}
      {activeTab === "predict" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Input Panel (5 cols) */}
          <div className="lg:col-span-5 space-y-4">
            <div className="apple-glass p-6 rounded-[28px] space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
                <span className="font-semibold text-[15px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <Target className="w-4 h-4 text-[#0071e3]" />
                  <span>Điểm Thi & Nguyện Vọng Dự Tuyển</span>
                </span>
                <span className="text-[13px] font-bold text-[#0071e3] dark:text-[#0a84ff] bg-[#0071e3]/10 px-2.5 py-0.5 rounded-full">
                  Tổng: {totalBaseScore.toFixed(2)}đ
                </span>
              </div>

              {/* Block Selection */}
              <div>
                <label className="text-[12px] font-medium text-[#86868b] dark:text-[#a1a1a6] mb-2 block">
                  Tổ hợp xét tuyển
                </label>
                <div className="grid grid-cols-6 gap-1.5">
                  {["A00", "A01", "B00", "C00", "D01", "D07"].map((block) => (
                    <button
                      key={block}
                      onClick={() => setSelectedBlock(block)}
                      className={`py-2 rounded-2xl text-[12px] font-semibold transition-all ${
                        selectedBlock === block
                          ? "bg-[#0071e3] text-white shadow-sm"
                          : "bg-black/[0.03] dark:bg-white/[0.06] text-[#1d1d1f] dark:text-[#f5f5f7] hover:bg-black/[0.07]"
                      }`}
                    >
                      {block}
                    </button>
                  ))}
                </div>
              </div>

              {/* 3 Subject Inputs */}
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: subjectNames.s1, val: sub1, set: setSub1 },
                  { label: subjectNames.s2, val: sub2, set: setSub2 },
                  { label: subjectNames.s3, val: sub3, set: setSub3 },
                ].map((item, idx) => (
                  <div key={idx} className="space-y-1">
                    <label className="text-[11px] text-[#86868b] block font-medium">
                      {item.label}
                    </label>
                    <input
                      type="number"
                      min="0"
                      max="10"
                      step="0.05"
                      value={item.val}
                      onChange={(e) => item.set(parseFloat(e.target.value) || 0)}
                      className="w-full px-3 py-2.5 text-[15px] font-semibold text-center rounded-2xl bg-black/[0.03] dark:bg-white/[0.06] border border-black/[0.06] dark:border-white/[0.08] text-[#1d1d1f] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#0071e3]"
                    />
                  </div>
                ))}
              </div>

              {/* University Select */}
              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#86868b] block">
                  Trường Đại Học
                </label>
                <select
                  value={selectedSchoolId}
                  onChange={(e) => {
                    setSelectedSchoolId(e.target.value);
                    setSelectedProgramCode("");
                  }}
                  className="w-full px-3.5 py-3 text-[13px] rounded-2xl bg-black/[0.03] dark:bg-white/[0.06] border border-black/[0.06] dark:border-white/[0.08] text-[#1d1d1f] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#0071e3]"
                >
                  {(universitiesData as any[]).map((u) => (
                    <option key={u.school_id} value={u.school_id} className="dark:bg-[#1c1c1e]">
                      [{u.school_id}] {u.school_name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Program Select */}
              <div className="space-y-1">
                <label className="text-[12px] font-medium text-[#86868b] block">
                  Ngành / Chuyên ngành đào tạo ({schoolPrograms.length} ngành)
                </label>
                <select
                  value={currentProgram?.score_code || ""}
                  onChange={(e) => setSelectedProgramCode(e.target.value)}
                  className="w-full px-3.5 py-3 text-[13px] rounded-2xl bg-black/[0.03] dark:bg-white/[0.06] border border-black/[0.06] dark:border-white/[0.08] text-[#1d1d1f] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#0071e3]"
                >
                  {schoolPrograms.map((p) => (
                    <option key={p.score_code} value={p.score_code} className="dark:bg-[#1c1c1e]">
                      [{p.score_code}] {p.score_name} (Điểm chuẩn: {p.latest_score})
                    </option>
                  ))}
                </select>
              </div>

              {/* Predict Button */}
              <button
                onClick={() => {
                  if (predictionResult && predictionResult.probability >= 0.85) {
                    confetti({ particleCount: 70, spread: 80, origin: { y: 0.6 } });
                  }
                }}
                className="w-full py-3.5 apple-button-primary flex items-center justify-center space-x-2 text-[14px]"
              >
                <Sparkles className="w-4 h-4" />
                <span>Thẩm Định Xác Suất Trúng Tuyển</span>
              </button>
            </div>
          </div>

          {/* Apple Result Card with Circular Activity Gauge (7 cols) */}
          <div className="lg:col-span-7 space-y-4">
            {predictionResult && (
              <div className="apple-glass p-7 rounded-[32px] space-y-6 relative overflow-hidden">
                {/* Header with program details & tier badge */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-5 border-b border-black/[0.06] dark:border-white/[0.08]">
                  <div>
                    <span className="text-[11px] font-bold uppercase tracking-wider text-[#86868b] dark:text-[#a1a1a6]">
                      {currentProgram?.school_name}
                    </span>
                    <h3 className="text-xl font-bold text-[#1d1d1f] dark:text-white tracking-tight mt-0.5">
                      {currentProgram?.score_name}
                    </h3>
                    <p className="text-[13px] text-[#86868b] dark:text-[#a1a1a6]">
                      Mã ngành: <span className="font-mono">{currentProgram?.score_code}</span> • Tổ hợp xét tuyển: <span className="font-bold">{selectedBlock}</span>
                    </p>
                  </div>

                  {/* Decision Tier Badge */}
                  <div 
                    className="px-4 py-2 rounded-full text-xs font-bold flex items-center space-x-2 shrink-0 border"
                    style={{
                      backgroundColor: `${predictionResult.tier.color}15`,
                      color: predictionResult.tier.color,
                      borderColor: `${predictionResult.tier.color}30`
                    }}
                  >
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: predictionResult.tier.color }} />
                    <span>{predictionResult.tier.label}</span>
                  </div>
                </div>

                {/* Circular Activity Gauge + Quantiles */}
                <div className="grid grid-cols-1 sm:grid-cols-12 gap-6 items-center">
                  {/* Apple Activity Ring */}
                  <div className="sm:col-span-5 flex flex-col items-center justify-center py-2">
                    <div className="relative w-36 h-36 flex items-center justify-center">
                      <svg className="w-full h-full transform -rotate-90">
                        {/* Background track circle */}
                        <circle
                          cx="72"
                          cy="72"
                          r={radius}
                          stroke="currentColor"
                          strokeWidth="11"
                          fill="transparent"
                          className="text-black/[0.05] dark:text-white/[0.08]"
                        />
                        {/* Progress stroke with rounded cap */}
                        <circle
                          cx="72"
                          cy="72"
                          r={radius}
                          stroke={predictionResult.tier.color}
                          strokeWidth="11"
                          strokeDasharray={circumference}
                          strokeDashoffset={strokeDashoffset}
                          strokeLinecap="round"
                          fill="transparent"
                          className="transition-all duration-700 ease-out"
                        />
                      </svg>
                      {/* Center Percent Label */}
                      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
                        <span className="text-3xl font-extrabold tracking-tight text-[#1d1d1f] dark:text-white">
                          {(predictionResult.probability * 100).toFixed(1)}%
                        </span>
                        <span className="text-[10px] uppercase font-bold text-[#86868b] tracking-wider mt-0.5">
                          Xác Suất Đỗ
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Quantile Breakdown Tiles */}
                  <div className="sm:col-span-7 space-y-3">
                    <span className="text-[12px] font-semibold text-[#86868b] dark:text-[#a1a1a6] block">
                      Dải Điểm Chuẩn Dự Báo (Quantile Regression)
                    </span>
                    <div className="grid grid-cols-3 gap-2">
                      <div className="p-3 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] border border-black/[0.05] dark:border-white/[0.08] text-center">
                        <span className="text-[10px] text-[#86868b] block font-medium">Q10 (Lạc quan)</span>
                        <span className="text-base font-bold text-[#34c759] dark:text-[#30d158] block mt-0.5">
                          {predictionResult.q10}đ
                        </span>
                      </div>
                      <div className="p-3 rounded-2xl bg-[#0071e3]/10 dark:bg-[#0a84ff]/15 border border-[#0071e3]/20 text-center">
                        <span className="text-[10px] text-[#0071e3] dark:text-[#0a84ff] block font-semibold">Q50 (Kỳ vọng)</span>
                        <span className="text-base font-extrabold text-[#0071e3] dark:text-[#0a84ff] block mt-0.5">
                          {predictionResult.q50}đ
                        </span>
                      </div>
                      <div className="p-3 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] border border-black/[0.05] dark:border-white/[0.08] text-center">
                        <span className="text-[10px] text-[#86868b] block font-medium">Q90 (Khắt khe)</span>
                        <span className="text-base font-bold text-[#ff3b30] dark:text-[#ff453a] block mt-0.5">
                          {predictionResult.q90}đ
                        </span>
                      </div>
                    </div>

                    <p className="text-[12px] text-[#86868b] dark:text-[#a1a1a6] leading-relaxed pt-1">
                      {predictionResult.tier.description}
                    </p>
                  </div>
                </div>

                {/* Score vs Cutoff Visual Slider Comparison */}
                <div className="space-y-2 pt-2">
                  <div className="flex justify-between text-[12px] font-medium">
                    <span className="text-[#86868b]">
                      Điểm thi của bạn: <strong className="text-[#1d1d1f] dark:text-white font-bold">{totalBaseScore}đ</strong>
                    </span>
                    <span className="text-[#86868b]">
                      Điểm chuẩn kỳ vọng: <strong className="text-[#1d1d1f] dark:text-white font-bold">{predictionResult.cutoffScore}đ</strong>
                    </span>
                  </div>
                  <div className="w-full h-3 bg-black/[0.06] dark:bg-white/[0.08] rounded-full overflow-hidden relative">
                    <div 
                      className="h-full rounded-full transition-all duration-700"
                      style={{ 
                        width: `${Math.min(100, (totalBaseScore / 30) * 100)}%`,
                        backgroundColor: predictionResult.tier.color 
                      }} 
                    />
                    {/* Marker for cutoff */}
                    <div 
                      className="absolute top-0 bottom-0 w-1 bg-[#1d1d1f] dark:bg-white z-10 shadow-sm"
                      style={{ left: `${(predictionResult.cutoffScore / 30) * 100}%` }}
                    />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex items-center space-x-3 pt-2">
                  <button
                    onClick={() => currentProgram && addToWishlist(currentProgram, predictionResult.probability)}
                    className="flex-1 py-3 apple-button-primary flex items-center justify-center space-x-2 text-[13px]"
                  >
                    <BookmarkPlus className="w-4 h-4" />
                    <span>Lưu Vào Giỏ Nguyện Vọng</span>
                  </button>
                  <button
                    onClick={() => setActiveTab("whatif")}
                    className="py-3 px-5 apple-button-secondary flex items-center space-x-2 text-[13px]"
                  >
                    <Sliders className="w-4 h-4" />
                    <span>Mô Phỏng What-If</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 1.2 CỐ VẤN & TỐI ƯU GIỎ NGUYỆN VỌNG (SMART WISHLIST) */}
      {/* ======================================================== */}
      {activeTab === "wishlist" && (
        <div className="space-y-6">
          {/* Strategy Balance Meter */}
          <div className="apple-glass p-7 rounded-[32px] space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <BookmarkPlus className="w-5 h-5 text-[#0071e3]" />
                  <span>Chiến Thuật Phân Bổ Nguyện Vọng Vàng (20% – 50% – 30%)</span>
                </h3>
                <p className="text-[13px] text-[#86868b] dark:text-[#a1a1a6] mt-0.5">
                  Tối ưu xác suất đỗ đại học qua 3 phân tầng rủi ro: Ước mơ (20%) - Vừa sức (50%) - An toàn lót đáy (30%)
                </p>
              </div>

              <span className={`px-3.5 py-1 rounded-full text-[12px] font-bold border ${
                strategyAnalysis.isBalanced 
                  ? "bg-[#34c759]/10 text-[#248a3d] dark:text-[#30d158] border-[#34c759]/20"
                  : "bg-[#ff9500]/10 text-[#d97706] dark:text-[#ff9f0a] border-[#ff9500]/20"
              }`}>
                {strategyAnalysis.isBalanced ? "✓ Cơ Cấu Đã Cân Bằng" : "⚠️ Cần Điều Chỉnh Tỷ Lệ"}
              </span>
            </div>

            {/* Apple Health-style Stacked Horizontal Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-[12px] font-semibold">
                <span className="text-[#ff3b30]">Ước mơ: {strategyAnalysis.dreamPct}% <span className="font-normal text-[#86868b]">(Mục tiêu 20%)</span></span>
                <span className="text-[#ff9500]">Vừa sức: {strategyAnalysis.targetPct}% <span className="font-normal text-[#86868b]">(Mục tiêu 50%)</span></span>
                <span className="text-[#34c759]">An toàn lót đáy: {strategyAnalysis.safetyPct}% <span className="font-normal text-[#86868b]">(Mục tiêu 30%)</span></span>
              </div>
              <div className="w-full h-3.5 bg-black/[0.06] dark:bg-white/[0.08] rounded-full overflow-hidden flex shadow-inner">
                <div style={{ width: `${strategyAnalysis.dreamPct}%` }} className="h-full bg-[#ff3b30] transition-all duration-300" title="Ước mơ" />
                <div style={{ width: `${strategyAnalysis.targetPct}%` }} className="h-full bg-[#ff9500] transition-all duration-300" title="Vừa sức" />
                <div style={{ width: `${strategyAnalysis.safetyPct}%` }} className="h-full bg-[#34c759] transition-all duration-300" title="An toàn" />
              </div>
            </div>

            {/* Warning Callouts */}
            {strategyAnalysis.warnings.length > 0 && (
              <div className="p-4 rounded-2xl bg-[#ff3b30]/10 border border-[#ff3b30]/20 space-y-1">
                {strategyAnalysis.warnings.map((w, i) => (
                  <p key={i} className="text-[13px] text-[#ff3b30] dark:text-[#ff453a] font-medium flex items-center space-x-2">
                    <AlertTriangle className="w-4 h-4 shrink-0" />
                    <span>{w}</span>
                  </p>
                ))}
              </div>
            )}
          </div>

          {/* Wishlist Items List */}
          <div className="space-y-3">
            <div className="flex items-center justify-between px-2">
              <h4 className="font-bold text-[15px] text-[#1d1d1f] dark:text-white">
                Thứ tự danh sách nguyện vọng ({wishlist.length} ngành)
              </h4>
              <button
                onClick={() => setActiveTab("recommend")}
                className="text-[13px] font-semibold text-[#0071e3] dark:text-[#0a84ff] hover:underline"
              >
                + Khám phá thêm ngành gợi ý
              </button>
            </div>

            <div className="space-y-2.5">
              {wishlist.map((item, idx) => (
                <div
                  key={item.id}
                  className="apple-glass p-5 rounded-[24px] apple-card-interactive flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="flex items-center space-x-3.5">
                    <span className="w-8 h-8 rounded-full bg-black/[0.04] dark:bg-white/[0.08] text-[#1d1d1f] dark:text-white flex items-center justify-center font-bold text-[13px]">
                      {item.order}
                    </span>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-[15px] text-[#1d1d1f] dark:text-white">
                          {item.majorName}
                        </span>
                        <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                          item.category === "dream" 
                            ? "bg-[#ff3b30]/10 text-[#ff3b30]" 
                            : item.category === "target" 
                            ? "bg-[#ff9500]/10 text-[#ff9500]" 
                            : "bg-[#34c759]/10 text-[#34c759]"
                        }`}>
                          {item.category === "dream" ? "Ước mơ (20%)" : item.category === "target" ? "Vừa sức (50%)" : "An toàn lót đáy (30%)"}
                        </span>
                      </div>
                      <p className="text-[12px] text-[#86868b] mt-0.5">
                        {item.schoolName} • Mã ngành: <span className="font-mono">{item.majorCode}</span> • Điểm chuẩn: <strong>{item.cutoffScore}đ</strong>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-4 self-end sm:self-center">
                    <div className="text-right">
                      <span className="text-[10px] uppercase font-bold text-[#86868b] block">Xác suất đỗ</span>
                      <span className="text-[16px] font-extrabold" style={{
                        color: item.probability >= 0.85 ? "#34c759" : item.probability >= 0.50 ? "#ff9500" : "#ff3b30"
                      }}>
                        {(item.probability * 100).toFixed(1)}%
                      </span>
                    </div>

                    {/* Order buttons */}
                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => moveOrder(idx, "up")}
                        disabled={idx === 0}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-black/[0.04] dark:bg-white/[0.08] disabled:opacity-20 hover:bg-black/[0.08]"
                      >
                        <ArrowUp className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => moveOrder(idx, "down")}
                        disabled={idx === wishlist.length - 1}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-black/[0.04] dark:bg-white/[0.08] disabled:opacity-20 hover:bg-black/[0.08]"
                      >
                        <ArrowDown className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => removeFromWishlist(item.id)}
                        className="w-7 h-7 rounded-full flex items-center justify-center bg-[#ff3b30]/10 text-[#ff3b30] hover:bg-[#ff3b30]/20"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setActiveTab("export")}
                className="py-3 px-6 apple-button-primary flex items-center space-x-2 text-[14px]"
              >
                <FileText className="w-4 h-4" />
                <span>Tiến Hành Xuất Phiếu Nguyện Vọng</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 1.3 MÔ PHỎNG WHAT-IF (ĐỘ NHẠY ĐIỂM SỐ) */}
      {/* ======================================================== */}
      {activeTab === "whatif" && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Sliders (6 cols) */}
          <div className="lg:col-span-6 space-y-4">
            <div className="apple-glass p-7 rounded-[32px] space-y-6">
              <div className="flex items-center justify-between pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
                <div>
                  <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                    <Sliders className="w-5 h-5 text-[#0071e3]" />
                    <span>Điều Khiển Kéo Điểm (Control Center)</span>
                  </h3>
                  <p className="text-[12px] text-[#86868b] mt-0.5">
                    Kéo tăng/giảm điểm từng môn xem độ nhạy xác suất trúng tuyển
                  </p>
                </div>

                <button
                  onClick={() => {
                    setWhatIfDelta1(0);
                    setWhatIfDelta2(0);
                    setWhatIfDelta3(0);
                  }}
                  className="text-[12px] font-semibold text-[#0071e3] hover:underline"
                >
                  Đặt lại 0
                </button>
              </div>

              {/* Slider 1 */}
              {[
                { name: subjectNames.s1, base: sub1, delta: whatIfDelta1, set: setWhatIfDelta1 },
                { name: subjectNames.s2, base: sub2, delta: whatIfDelta2, set: setWhatIfDelta2 },
                { name: subjectNames.s3, base: sub3, delta: whatIfDelta3, set: setWhatIfDelta3 },
              ].map((s, i) => (
                <div key={i} className="p-4 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] space-y-2">
                  <div className="flex justify-between text-[13px]">
                    <span className="font-semibold text-[#1d1d1f] dark:text-white">
                      {s.name}: <span className="text-[#0071e3] font-bold">{(s.base + s.delta).toFixed(2)}đ</span>
                    </span>
                    <span className={`font-mono font-bold text-[12px] ${s.delta > 0 ? "text-[#34c759]" : s.delta < 0 ? "text-[#ff3b30]" : "text-[#86868b]"}`}>
                      {s.delta > 0 ? `+${s.delta.toFixed(2)}đ` : `${s.delta.toFixed(2)}đ`}
                    </span>
                  </div>
                  <input
                    type="range"
                    min="-2.0"
                    max="2.0"
                    step="0.25"
                    value={s.delta}
                    onChange={(e) => s.set(parseFloat(e.target.value))}
                    className="apple-slider"
                  />
                </div>
              ))}
            </div>
          </div>

          {/* Sensitivity Impact Card (6 cols) */}
          <div className="lg:col-span-6 space-y-4">
            {whatIfResult && (
              <div className="apple-glass p-7 rounded-[32px] space-y-6">
                <div>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-[#86868b]">
                    Kết Quả Mô Phỏng
                  </span>
                  <h4 className="text-xl font-bold text-[#1d1d1f] dark:text-white tracking-tight mt-0.5">
                    {currentProgram?.score_name}
                  </h4>
                  <p className="text-[13px] text-[#86868b]">
                    Tổng điểm thi sau mô phỏng: <strong className="text-[#0071e3] font-bold">{totalWhatIfScore.toFixed(2)}đ</strong>
                  </p>
                </div>

                {/* Before vs After Cards */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] text-center space-y-1">
                    <span className="text-[11px] text-[#86868b] uppercase font-semibold">Điểm Thực Tế</span>
                    <div className="text-3xl font-extrabold text-[#1d1d1f] dark:text-white">
                      {((predictionResult?.probability || 0) * 100).toFixed(1)}%
                    </div>
                    <span className="text-[11px] text-[#86868b] block">{totalBaseScore} điểm</span>
                  </div>

                  <div className="p-4 rounded-2xl bg-[#0071e3]/10 dark:bg-[#0a84ff]/15 border border-[#0071e3]/20 text-center space-y-1">
                    <span className="text-[11px] text-[#0071e3] dark:text-[#0a84ff] uppercase font-semibold">Sau Khi Kéo Điểm</span>
                    <div className="text-3xl font-extrabold text-[#0071e3] dark:text-[#0a84ff]">
                      {(whatIfResult.probability * 100).toFixed(1)}%
                    </div>
                    <span className="text-[11px] font-bold text-[#34c759] block">
                      {whatIfResult.probDelta >= 0 ? `+${(whatIfResult.probDelta * 100).toFixed(1)}% cơ hội` : `${(whatIfResult.probDelta * 100).toFixed(1)}% cơ hội`}
                    </span>
                  </div>
                </div>

                {/* AI Advice */}
                <div className="p-4 rounded-2xl bg-black/[0.03] dark:bg-white/[0.06] border border-black/[0.05] dark:border-white/[0.08] space-y-1.5">
                  <span className="text-[13px] font-bold text-[#1d1d1f] dark:text-white flex items-center space-x-1.5">
                    <Sparkles className="w-4 h-4 text-[#ff9500]" />
                    <span>Chiến Lược Ôn Luyện Đòn Bẩy</span>
                  </span>
                  <p className="text-[13px] text-[#86868b] dark:text-[#a1a1a6] leading-relaxed">
                    Tăng thêm {(totalWhatIfScore - totalBaseScore).toFixed(2)} điểm ở môn {subjectNames.s1} tạo ra bước nhảy lớn nhất về phân vị. Hãy tập trung 60% thời lượng ôn luyện môn này để tối đa hóa hiệu quả kéo điểm an toàn.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 1.4 GỢI Ý NGÀNH THEO KHOẢNG ĐIỂM */}
      {/* ======================================================== */}
      {activeTab === "recommend" && (
        <div className="space-y-5">
          <div className="apple-glass p-7 rounded-[32px] space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <Sparkles className="w-5 h-5 text-[#ff9500]" />
                  <span>Gợi Ý Ngành Xét Tuyển Xác Suất Đỗ Cao (≥ 70%)</span>
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  Lọc theo mức điểm thi <strong className="text-[#0071e3]">{totalBaseScore} điểm</strong> ({selectedBlock})
                </p>
              </div>

              {/* Search */}
              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 absolute left-3.5 top-3 text-[#86868b]" />
                <input
                  type="text"
                  placeholder="Lọc tên ngành, trường..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-[13px] rounded-full bg-black/[0.04] dark:bg-white/[0.08] border border-black/[0.06] dark:border-white/[0.08] text-[#1d1d1f] dark:text-white focus:outline-none focus:ring-2 focus:ring-[#0071e3]"
                />
              </div>
            </div>

            {/* List Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-left text-[13px]">
                <thead>
                  <tr className="border-b border-black/[0.06] dark:border-white/[0.08] text-[#86868b] font-medium text-[11px] uppercase tracking-wider">
                    <th className="py-3 px-3">Trường</th>
                    <th className="py-3 px-3">Tên Ngành</th>
                    <th className="py-3 px-3 text-center">Điểm Chuẩn 2024</th>
                    <th className="py-3 px-3 text-center">Xác Suất Đỗ</th>
                    <th className="py-3 px-3 text-right">Thao Tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-black/[0.04] dark:divide-white/[0.04]">
                  {recommendedPrograms.map((p, idx) => {
                    const diff = totalBaseScore - p.latest_score;
                    const prob = Math.min(0.99, Math.max(0.70, 1 / (1 + Math.exp(-1.35 * diff))));
                    return (
                      <tr key={idx} className="hover:bg-black/[0.02] dark:hover:bg-white/[0.03] transition-colors">
                        <td className="py-3 px-3 font-semibold text-[#1d1d1f] dark:text-white">
                          <span className="text-[10px] px-2 py-0.5 rounded-md font-mono bg-black/[0.04] dark:bg-white/[0.08] mr-2">
                            {p.school_id}
                          </span>
                          {p.school_name}
                        </td>
                        <td className="py-3 px-3 text-[#1d1d1f] dark:text-[#f5f5f7]">
                          {p.score_name}
                        </td>
                        <td className="py-3 px-3 text-center font-bold">
                          {p.latest_score}đ
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-[#34c759]/10 text-[#34c759]">
                            {(prob * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-3 px-3 text-right">
                          <button
                            onClick={() => addToWishlist(p, prob)}
                            className="px-3.5 py-1.5 rounded-full text-[12px] font-semibold text-[#0071e3] bg-[#0071e3]/10 hover:bg-[#0071e3]/20 transition-all"
                          >
                            + Chọn Nguyện Vọng
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 1.5 TRA CỨU VỊ THẾ PHÂN VỊ (CDF EXPLORER) */}
      {/* ======================================================== */}
      {activeTab === "cdf" && (
        <div className="space-y-6">
          <div className="apple-glass p-7 rounded-[32px] space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[17px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <BarChart2 className="w-5 h-5 text-[#0071e3]" />
                  <span>Tra Cứu Vị Thế Phân Vị Quốc Gia (CDF Explorer)</span>
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  Đo lường chính xác thứ tự xếp hạng điểm số trên quy mô 10 triệu bản ghi
                </p>
              </div>

              {/* Block Switcher */}
              <div className="apple-segmented-group">
                {["A00", "A01", "B00", "C00", "D01"].map((b) => (
                  <button
                    key={b}
                    onClick={() => setSelectedBlock(b)}
                    className={`px-3 py-1 apple-segmented-item ${
                      selectedBlock === b ? "apple-segmented-item-active" : "text-[#86868b]"
                    }`}
                  >
                    Khối {b}
                  </button>
                ))}
              </div>
            </div>

            {/* Apple Stat Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-4 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] text-center">
                <span className="text-[11px] text-[#86868b] block font-medium">Điểm xét tuyển</span>
                <span className="text-2xl font-bold text-[#0071e3] block mt-0.5">{totalBaseScore}đ</span>
              </div>
              <div className="p-4 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] text-center">
                <span className="text-[11px] text-[#86868b] block font-medium">Vị thế toàn quốc</span>
                <span className="text-2xl font-bold text-[#34c759] block mt-0.5">
                  Top {(lookupRankPercentile(totalBaseScore) * 100).toFixed(2)}%
                </span>
              </div>
              <div className="p-4 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] text-center">
                <span className="text-[11px] text-[#86868b] block font-medium">Số thí sinh trên bạn</span>
                <span className="text-2xl font-bold text-[#1d1d1f] dark:text-white block mt-0.5">
                  ~{Math.round(278000 * lookupRankPercentile(totalBaseScore)).toLocaleString()}
                </span>
              </div>
              <div className="p-4 rounded-2xl bg-black/[0.03] dark:bg-white/[0.05] text-center">
                <span className="text-[11px] text-[#86868b] block font-medium">Tỷ lệ tích lũy F(x)</span>
                <span className="text-2xl font-bold text-[#af52de] block mt-0.5">
                  {((1 - lookupRankPercentile(totalBaseScore)) * 100).toFixed(1)}%
                </span>
              </div>
            </div>

            {/* Apple Stock Style CDF Area Graph */}
            <div className="h-72 w-full pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={cdfList} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="appleCdfGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0071e3" stopOpacity={0.35} />
                      <stop offset="95%" stopColor="#0071e3" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="score" tick={{ fontSize: 11 }} stroke="#86868b" unit="đ" />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} stroke="#86868b" tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
                  <Tooltip 
                    formatter={(val: any) => [`${(Number(val) * 100).toFixed(2)}%`, "Tỷ lệ tích lũy"]}
                    contentStyle={{
                      backgroundColor: "rgba(255, 255, 255, 0.85)",
                      backdropFilter: "blur(20px)",
                      borderRadius: "16px",
                      border: "1px solid rgba(0, 0, 0, 0.08)",
                      boxShadow: "0 8px 30px rgba(0,0,0,0.12)"
                    }}
                  />
                  <Area type="monotone" dataKey="cdf_leq" stroke="#0071e3" strokeWidth={2.5} fill="url(#appleCdfGrad)" />
                  <ReferenceLine 
                    x={totalBaseScore} 
                    stroke="#ff3b30" 
                    strokeWidth={2} 
                    strokeDasharray="4 4"
                    label={{ value: `Bạn: ${totalBaseScore}đ`, position: "top", fill: "#ff3b30", fontSize: 11 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* 1.6 XUẤT PHIẾU NGUYỆN VỌNG */}
      {/* ======================================================== */}
      {activeTab === "export" && (
        <div className="space-y-6">
          <div className="apple-glass p-7 rounded-[32px] space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-black/[0.06] dark:border-white/[0.08]">
              <div>
                <h3 className="font-bold text-[18px] text-[#1d1d1f] dark:text-white flex items-center space-x-2">
                  <FileText className="w-5 h-5 text-[#0071e3]" />
                  <span>Phiếu Đăng Ký Nguyện Vọng Tuyển Sinh Đại Học 2026</span>
                </h3>
                <p className="text-[13px] text-[#86868b] mt-0.5">
                  Phương án xét tuyển tối ưu theo chiến thuật vàng 20% Ước mơ - 50% Vừa sức - 30% An toàn
                </p>
              </div>

              <div className="flex items-center space-x-3">
                <button
                  onClick={() => window.print()}
                  className="py-2.5 px-5 apple-button-secondary flex items-center space-x-2 text-[13px]"
                >
                  <Printer className="w-4 h-4" />
                  <span>In Phiếu / PDF</span>
                </button>
                <button
                  onClick={() => {
                    const csv = "data:text/csv;charset=utf-8,\uFEFF" +
                      ["Thứ Tự,Mã Trường,Tên Trường,Mã Ngành,Tên Ngành,Tổ Hợp,Điểm Chuẩn,Xác Suất,Phân Tầng"]
                      .concat(wishlist.map(w => `${w.order},${w.schoolId},"${w.schoolName}",${w.majorCode},"${w.majorName}",${w.block},${w.cutoffScore},${(w.probability*100).toFixed(1)}%,${w.category}`))
                      .join("\n");
                    const link = document.createElement("a");
                    link.href = encodeURI(csv);
                    link.download = `Phieu_Nguyen_Vong_${totalBaseScore}d.csv`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                  }}
                  className="py-2.5 px-5 apple-button-primary flex items-center space-x-2 text-[13px]"
                >
                  <FileSpreadsheet className="w-4 h-4" />
                  <span>Xuất File Excel</span>
                </button>
              </div>
            </div>

            {/* Certificate Preview */}
            <div className="p-8 rounded-[24px] bg-white dark:bg-[#121214] border border-black/[0.08] dark:border-white/[0.1] shadow-sm space-y-6">
              <div className="text-center space-y-1">
                <h4 className="font-bold text-[13px] uppercase tracking-wider text-[#86868b]">
                  BỘ GIÁO DỤC VÀ ĐÀO TẠO
                </h4>
                <h5 className="font-bold text-xl text-[#1d1d1f] dark:text-white uppercase tracking-tight">
                  DANH SÁCH NGUYỆN VỌNG XÉT TUYỂN CHÍNH THỨC
                </h5>
                <p className="text-[12px] text-[#86868b]">
                  Thí sinh: <strong>NGUYỄN VĂN AN</strong> • SBD: <strong>01029384</strong> • Khối {selectedBlock}: <strong>{totalBaseScore} điểm</strong>
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-[13px]">
                  <thead>
                    <tr className="border-b border-black/[0.08] dark:border-white/[0.08] text-[#86868b] font-semibold text-[11px] uppercase tracking-wider">
                      <th className="py-2.5 px-3 text-center">Thứ tự</th>
                      <th className="py-2.5 px-3">Mã Trường</th>
                      <th className="py-2.5 px-3">Tên Trường</th>
                      <th className="py-2.5 px-3">Tên Ngành</th>
                      <th className="py-2.5 px-3 text-center">Tổ Hợp</th>
                      <th className="py-2.5 px-3 text-center">Xác Suất</th>
                      <th className="py-2.5 px-3 text-center">Phân Tầng</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-black/[0.04] dark:divide-white/[0.04]">
                    {wishlist.map((w) => (
                      <tr key={w.id}>
                        <td className="py-3 px-3 text-center font-bold text-[#0071e3]">{w.order}</td>
                        <td className="py-3 px-3 font-semibold">{w.schoolId}</td>
                        <td className="py-3 px-3">{w.schoolName}</td>
                        <td className="py-3 px-3 font-medium">{w.majorName}</td>
                        <td className="py-3 px-3 text-center font-mono">{w.block}</td>
                        <td className="py-3 px-3 text-center font-bold text-[#34c759]">
                          {(w.probability * 100).toFixed(1)}%
                        </td>
                        <td className="py-3 px-3 text-center">
                          <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            w.category === "dream" ? "bg-[#ff3b30]/10 text-[#ff3b30]" :
                            w.category === "target" ? "bg-[#ff9500]/10 text-[#ff9500]" :
                            "bg-[#34c759]/10 text-[#34c759]"
                          }`}>
                            {w.category === "dream" ? "Ước mơ" : w.category === "target" ? "Vừa sức" : "An toàn lót đáy"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
