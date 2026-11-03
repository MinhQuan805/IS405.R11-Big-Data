"""Mathematical Formulations and Core Analytical Functions.
Pure functions implementing Module 1, 2, 3, 4 mathematical specifications.
"""

import math
from typing import Optional

def standard_normal_cdf(z: float) -> float:
    """Hàm phân phối tích lũy chuẩn tắc Phi(z) = 0.5 * (1 + erf(z / sqrt(2)))"""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def calculate_admission_probability(
    student_rank_pct: float,
    predicted_mean: float,
    predicted_variance: float
) -> float:
    """Công thức suy luận Module 4: P(Pass) = Phi((mu - r) / sigma)"""
    sigma = math.sqrt(max(predicted_variance, 1e-6))
    z = (predicted_mean - student_rank_pct) / sigma
    prob = standard_normal_cdf(z)
    return max(0.0, min(1.0, prob))

def classify_decision_tier(probability: float) -> str:
    """Phân tầng khuyến nghị mức độ an toàn của nguyện vọng"""
    if probability >= 0.80:
        return "An toàn (Safe)"
    elif probability >= 0.50:
        return "Cạnh tranh (Competitive)"
    else:
        return "Rủi ro cao (High Risk)"

def cold_start_percentile_estimation(
    school_mean_pct: float, 
    major_mean_pct: float, 
    weight: float = 0.5
) -> float:
    """Công thức tiên nghiệm tổ hợp lồi giải quyết khởi đầu lạnh cho ngành mới"""
    return weight * school_mean_pct + (1.0 - weight) * major_mean_pct

