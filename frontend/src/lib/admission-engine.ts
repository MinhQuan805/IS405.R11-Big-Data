// Pure mathematical formulations matching admission_core specs

/**
 * Standard Normal Cumulative Distribution Function Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))
 */
export function standardNormalCdf(z: number): number {
  return 0.5 * (1.0 + erf(z / Math.SQRT2));
}

function erf(x: number): number {
  // Abramowitz and Stegun formula 7.1.26 approximation
  const a1 = 0.254829592;
  const a2 = -0.284496736;
  const a3 = 1.421413741;
  const a4 = -1.453152027;
  const a5 = 1.061405429;
  const p = 0.3275911;

  const sign = x < 0 ? -1 : 1;
  const absX = Math.abs(x);
  const t = 1.0 / (1.0 + p * absX);
  const y = 1.0 - (((((a5 * t + a4) * t + a3) * t + a2) * t + a1) * t) * Math.exp(-absX * absX);

  return sign * y;
}

/**
 * Module 4 formula: P(Pass) = Phi((mu - r) / sigma)
 * Where r is student rank percentile (0 is top rank, 1 is bottom rank),
 * mu is predicted cutoff percentile mean, and sigma = sqrt(variance).
 */
export function calculateAdmissionProbability(
  studentRankPct: number,
  predictedMean: number,
  predictedVariance: number
): number {
  if (predictedVariance <= 0) predictedVariance = 0.001;
  const sigma = Math.sqrt(Math.max(predictedVariance, 0.0001));
  const z = (predictedMean - studentRankPct) / sigma;
  const prob = standardNormalCdf(z);
  return Math.max(0.0, Math.min(1.0, prob));
}

export type DecisionTier = "safe" | "competitive" | "risky";

export function getDecisionTier(probability: number): {
  tier: DecisionTier;
  label: string;
  badgeClass: string;
  color: string;
  description: string;
} {
  if (probability >= 0.85) {
    return {
      tier: "safe",
      label: "An toàn (>85%)",
      badgeClass: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20",
      color: "#10b981",
      description: "Cơ hội trúng tuyển rất cao. Điểm số nằm trong vùng chắc chắn của ngành."
    };
  } else if (probability >= 0.50) {
    return {
      tier: "competitive",
      label: "Cạnh tranh (50-85%)",
      badgeClass: "bg-amber-500/10 text-amber-600 dark:text-amber-400 border-amber-500/20",
      color: "#f59e0b",
      description: "Khả năng đỗ vừa sức. Cần cân nhắc thứ tự nguyện vọng hợp lý."
    };
  } else {
    return {
      tier: "risky",
      label: "Mạo hiểm (<50%)",
      badgeClass: "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20",
      color: "#f43f5e",
      description: "Nguy cơ trượt cao. Nên dùng làm nguyện vọng ước mơ 1 hoặc 2."
    };
  }
}

export interface WishlistItem {
  id: string;
  order: number;
  schoolId: string;
  schoolName: string;
  majorCode: string;
  majorName: string;
  block: string;
  cutoffScore: number;
  userScore: number;
  probability: number;
  tier: DecisionTier;
  category: "dream" | "target" | "safety"; // Ước mơ (20%) - Vừa sức (50%) - An toàn (30%)
}

export function classifyWishlistCategory(probability: number): "dream" | "target" | "safety" {
  if (probability < 0.60) {
    return "dream";
  } else if (probability <= 0.85) {
    return "target";
  } else {
    return "safety";
  }
}

export function analyzeWishlistStrategy(items: WishlistItem[]): {
  dreamPct: number;
  targetPct: number;
  safetyPct: number;
  warnings: string[];
  recommendations: string[];
  isBalanced: boolean;
} {
  const total = items.length;
  if (total === 0) {
    return {
      dreamPct: 0,
      targetPct: 0,
      safetyPct: 0,
      warnings: ["Giỏ nguyện vọng hiện đang trống. Hãy thêm nguyện vọng để phân tích chiến thuật."],
      recommendations: ["Thêm tối thiểu 4-6 nguyện vọng để đảm bảo phân bổ rủi ro an toàn."],
      isBalanced: false
    };
  }

  const dreamCount = items.filter((i) => i.category === "dream").length;
  const targetCount = items.filter((i) => i.category === "target").length;
  const safetyCount = items.filter((i) => i.category === "safety").length;

  const dreamPct = Math.round((dreamCount / total) * 100);
  const targetPct = Math.round((targetCount / total) * 100);
  const safetyPct = Math.round((safetyCount / total) * 100);

  const warnings: string[] = [];
  const recommendations: string[] = [];

  if (safetyCount === 0) {
    warnings.push("⚠️ Cảnh báo nguy hiểm: Bạn chưa có bất kỳ nguyện vọng 'An toàn lót đáy' nào (>85%)! Rất dễ rơi vào tình trạng trượt toàn bộ các trường.");
  }
  if (dreamPct > 40) {
    warnings.push("⚠️ Tỷ lệ nguyện vọng ước mơ quá cao (>40%). Bạn đang mạo hiểm quá mức theo khuyến nghị của các chuyên gia.");
  }
  if (targetPct < 30 && total >= 3) {
    recommendations.push("Nên bổ sung thêm các ngành thuộc nhóm 'Vừa sức' (xác suất 60% - 85%) để tăng cơ hội vào đúng năng lực.");
  }
  if (safetyCount >= 1 && dreamCount >= 1 && targetCount >= 1) {
    recommendations.push("✅ Cơ cấu nguyện vọng đã tiệm cận chiến thuật vàng: 20% Ước mơ - 50% Vừa sức - 30% An toàn lót đáy!");
  }

  const isBalanced = safetyCount > 0 && dreamPct <= 35 && targetPct >= 35;

  return {
    dreamPct,
    targetPct,
    safetyPct,
    warnings,
    recommendations,
    isBalanced
  };
}
