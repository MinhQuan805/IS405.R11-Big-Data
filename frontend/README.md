# UniAdmit AI - Frontend Web Application
> **Hệ Thống Phân Tích & Dự Báo Tuyển Sinh Đại Học (Big Data & MLOps)**  
> Thiết kế chuẩn **Apple Human Interface Guidelines (Apple Design System)** với **Next.js 16 + Tailwind CSS v4 + Lucide Icons + Recharts**.

---

## 🌟 Tổng Quan 4 Phân Hệ Chức Năng

### 1. Phân Hệ Thí Sinh & Học Sinh (Cá Nhân Hóa Xét Tuyển)
- **1.1. Dự báo xác suất trúng tuyển liên tục**:
  - Nhập điểm 3 môn + chọn tổ hợp (A00, A01, B00, C00, D01, D07,...) + chọn trường và ngành đào tạo thực tế.
  - Trả về xác suất đỗ (%) kèm dải điểm chuẩn tin cậy Quantile (10% - 50% - 90%).
  - Đánh giá mức độ rủi ro trực quan: **An toàn (>85%)**, **Cạnh tranh (50-85%)**, **Mạo hiểm (<50%)**.
- **1.2. Cố vấn & Tối ưu giỏ nguyện vọng (Smart Wishlist)**:
  - Phân loại danh sách nguyện vọng theo chiến thuật vàng: **Ước mơ (20%) - Vừa sức (50%) - An toàn lót đáy (30%)**.
  - Tự động cảnh báo rủi ro nếu thiếu nguyện vọng bảo hiểm an toàn.
  - Cho phép sắp xếp thứ tự ưu tiên (NV1, NV2, NV3,...).
- **1.3. Mô phỏng "What-If" (Độ nhạy điểm số)**:
  - Kéo thanh trượt điều chỉnh tăng/giảm điểm từng môn xem sự biến thiên xác suất đỗ ($\Delta P$).
  - AI tư vấn định hướng ôn thi kéo điểm môn nào mang lại hiệu quả đòn bẩy cao nhất.
- **1.4. Gợi ý ngành theo khoảng điểm**:
  - Nhập tổng điểm -> Lọc và gợi ý danh sách toàn bộ các trường/ngành có xác suất đỗ $\ge 70\%$.
- **1.5. Tra cứu vị thế phân vị (CDF Explorer)**:
  - Tra cứu xem điểm của mình đứng thứ bao nhiêu trong toàn quốc theo tổ hợp môn dựa trên hàm tích lũy CDF $F(x)$.
- **1.6. Xuất phiếu nguyện vọng**:
  - Xem trước phiếu theo chuẩn biểu mẫu của Bộ Giáo dục & Đào tạo.
  - Xuất phiếu sang file Excel (CSV) hoặc in PDF trực tiếp.

---

### 2. Phân Hệ Giáo Viên & Chuyên Viên Tư Vấn
- **2.1. Tư vấn hàng loạt cho lớp học (Batch Counseling)**:
  - Nạp danh sách điểm của cả lớp (hỗ trợ dữ liệu mẫu Lớp 12A1 gồm 15 học sinh đa dạng năng lực).
  - Tự động phân loại học lực: Xuất sắc, Giỏi, Khá, Trung bình khá.
  - Tự động gợi ý 2 trường/ngành phù hợp nhất cho từng em và xuất file báo cáo tổng hợp Excel.
- **2.2. Báo cáo phân tích phổ điểm lớp**:
  - Biểu đồ phân phối đối sánh (Histogram) giữa phổ điểm lớp và phổ điểm toàn quốc của Bộ GD&ĐT.
  - Thống kê Điểm trung bình, Trung vị và Tỷ lệ đạt điểm Top Tier ($\ge 26.0$ điểm).
- **2.3. So sánh đối đầu giữa các trường / ngành (Head-to-Head)**:
  - Đặt 2 - 3 trường lên bàn cân so sánh:
    - Diễn biến điểm chuẩn 5 năm (2020 - 2025).
    - Biểu đồ mạng nhện đa chiều (Chỉ tiêu, Google Trends mùa thi, Độ cạnh tranh, Cơ hội việc làm).

---

### 3. Dashboard Google Trends & Dữ Liệu Lớn (Data Analytics)
- **3.1. Radar nhịp mùa thi (Seasonal Trends)**:
  - Biểu đồ chuỗi thời gian 12 tháng phản ánh đỉnh nhọn mức độ quan tâm của xã hội vào mùa thi (Tháng 6 - Tháng 8).
- **3.2. So sánh độ "nóng" giữa các trường / ngành**:
  - Bảng xếp hạng độ nóng trực tuyến các khối ngành chiến lược: Công nghệ thông tin & AI, Bán dẫn & Vi mạch (+142.6% YoY), Kinh tế số, Y Dược.
- **3.3. Bản đồ quan tâm theo tỉnh thành (Geo Trends)**:
  - Bản đồ nhiệt thể hiện thí sinh tại các tỉnh thành (Hà Nội, TP.HCM, Đà Nẵng, Nghệ An, Nam Định, v.v.) tìm kiếm nhiều nhất.
- **3.4. Tương quan Google Trends vs Điểm chuẩn**:
  - Biểu đồ đường kép chứng minh mối liên hệ thống kê chặt chẽ ($r = 0.93$): Độ nóng tìm kiếm tăng trong năm trước dẫn đến điểm chuẩn năm sau tăng theo.

---

### 4. Dashboard MLOps & Big Data (Phục Vụ Chấm Điểm Đồ Án)
- **4.1. Data Pipeline Monitor**:
  - Thống kê quy mô kiến trúc Lakehouse:
    - **Bronze**: 9.66M+ bản ghi điểm thi thô (CT2006: 8.5M, CT2018: 1.1M).
    - **Silver**: 9.65M bản ghi Parquet sạch sau khi khử 10.8K dòng lặp và chuẩn hóa tiếng Việt.
    - **Gold**: 33,297 dòng ma trận đặc trưng Contract 3.0.
  - Kiến trúc Ports & Adapters: So sánh Local Pandas vs Apache Spark 4.3.0.
- **4.2. Tra cứu CDF siêu tốc (< 10ms)**:
  - Công cụ benchmark tương tác: Đo tốc độ tra cứu phân vị trên 10 triệu bản ghi.
  - Chứng minh tốc độ **3.4ms** của PySpark Precomputed Index (nhanh gấp **>700 lần** so với Naive Fullscan ~2,450ms).
- **4.3. Đánh giá mô hình & Tầm quan trọng đặc trưng**:
  - Trực quan hóa đầy đủ 15 đặc trưng của hợp đồng **Contract 3.0** (Gain % và SHAP).
  - Bảng kiểm định sai số qua các năm (Out-of-time Expanding Window 2020 - 2025): RMSE, R², Coverage 80%.
  - Minh chứng đạt chuẩn Quality Gate với Sàn sai số Bayes MSE = 0.02283.
- **4.4. API Serving Playground**:
  - Trình kiểm thử REST API thời gian thực (`POST /api/v2/predict/admission-probability`).
  - Gửi payload JSON và nhận kết quả tức thì với độ trễ $p50 \approx 15.8\text{ms}$.

---

## 🚀 Hướng Dẫn Cài Đặt & Chạy Ứng Dụng

### Yêu Cầu Môi Trường
- **Node.js**: v18+ hoặc v20+ (Khuyến nghị Node.js LTS)
- **npm**: v9+ hoặc v10+

### Khởi Chạy Frontend
```bash
# 1. Di chuyển vào thư mục frontend
cd frontend

# 2. Cài đặt các thư viện (nếu cần)
npm install

# 3. Khởi chạy máy chủ phát triển
npm run dev -- -p 3005
```

Truy cập trình duyệt tại: **`http://localhost:3005`** (hoặc `http://localhost:3000`).

### Biên Dịch Production
```bash
npm run build
npm run start
```
