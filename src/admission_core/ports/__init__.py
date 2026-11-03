"""Abstract Ports (Interfaces) for the Admission Core Framework.
Defines the contract for pluggable execution adapters (Ports & Adapters Architecture).
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseIngestionPort(ABC):
    """Cổng trừu tượng cho công đoạn Thu thập & Nạp dữ liệu"""
    @abstractmethod
    def ingest(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Nạp hoặc cào dữ liệu từ các nguồn, trả về từ điển đường dẫn file đầu ra.
        """
        pass

class BaseCDFPort(ABC):
    """Cổng trừu tượng cho Module 2: Tính toán Empirical CDF và Rank Percentile"""
    @abstractmethod
    def compute_cdf(
        self, 
        raw_dist_sources: Dict[str, str], 
        output_uri: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Tính toán bảng phân phối tích lũy và hàm sống sót 1 - F(s).
        """
        pass

class BaseFeaturePipelinePort(ABC):
    """Cổng trừu tượng cho Module 1 & 3: Xây dựng Ma trận Đặc trưng Đa tầng"""
    @abstractmethod
    def build_features(
        self, 
        input_data_uris: Dict[str, str], 
        output_feature_uri: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Tính toán các biến trễ đa tầng, vị thế tương đối, Trends và tương tác bậc 2.
        """
        pass

class BaseTrainerPort(ABC):
    """Cổng trừu tượng cho Module 3: Huấn luyện Mô hình & Tối ưu Siêu tham số"""
    @abstractmethod
    def train_and_evaluate(
        self, 
        feature_matrix_uri: str, 
        output_model_dir: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Huấn luyện point regressor và quantile regressors, trả về từ điển chỉ số đánh giá.
        """
        pass

class BaseInferencePort(ABC):
    """Cổng trừu tượng cho Module 4: Phục vụ Suy luận Trực tuyến"""
    @abstractmethod
    def predict(
        self, 
        student_input: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Dự đoán xác suất trúng tuyển và khuyến nghị phân tầng cho thí sinh.
        """
        pass

