# Đánh giá notebook `feature-analysis-and-model-proposal.ipynb`

Ngày rà soát: 16/10/2026. Phạm vi: notebook, dữ liệu trong `data-raw/` và `data-cleaned/`, hai script tạo dữ liệu sạch `cutoff_scores.py` và `clean_trends.py`. Các số liệu dưới đây lấy trực tiếp từ CSV hiện có. Tôi chạy riêng cell 3 và cell 55 để kiểm tra kết quả trích xuất đặc trưng; chưa chạy lại toàn bộ notebook vì môi trường `.venv` thiếu `statsmodels` (notebook có import, `requirements.txt` chưa khai báo).

## Kết luận ngắn

Notebook có cấu trúc khám phá hợp lý ở mức đề cương: có khảo sát độ phủ, chuỗi thời gian, danh mục đặc trưng và ý tưởng chia tập theo năm. Tuy nhiên, **chưa đủ tin cậy để dùng các Tier đặc trưng, các con số tương quan/F-test/importance và lựa chọn mô hình như kết luận thực nghiệm**. Một số đặc trưng quan trọng được tính sai hoặc không biến thiên; khóa lịch sử không xác định duy nhất quan sát; đặc trưng dùng dữ liệu sau thời điểm dự đoán; và một số diễn giải không khớp dữ liệu hiện tại.

Ưu tiên sửa: (1) xác định đơn vị quan sát và mốc dự báo, (2) sửa khóa/lag/thang điểm, (3) kiểm kê đủ thuộc tính và vết dữ liệu, (4) chỉ sau đó chạy lại thẩm định theo thời gian.

## 1. Tính đầy đủ và vết dữ liệu

### Độ phủ thực tế

| Tập dữ liệu | Số dòng | Được notebook dùng như thế nào | Phần cần kiểm tra thêm |
|---|---:|---|---|
| Điểm chuẩn thô | 147.671; 15 cột | Không đọc trực tiếp | Hai cột `score_formula`, `score_is_converted_score` bị bỏ ngay ở pipeline làm sạch. Cần kiểm kê lý do loại từng dòng và tác động của chuẩn hóa thang điểm. |
| Điểm chuẩn sạch | 101.466; 13 cột | Cell 3 đọc toàn bộ; cell 55 chỉ giữ 57.400 dòng `Điểm thi THPT` | 44.066 dòng thuộc 12 phương thức khác không vào phân tích đặc trưng/mô hình. Nếu chỉ dự báo THPT, phải tuyên bố rõ phạm vi; nếu dự báo mọi phương thức, thiết kế hiện tại chưa đầy đủ. |
| Danh mục ngành | 506; 6 cột | Chỉ dùng `score_codes`, `major_group_name`, `major_name` để gán nhãn | `major_group_id`, `major_id`, `major_description` chưa kiểm tra; phép `drop_duplicates(score_code)` gán tùy ý khi mã ánh xạ nhiều ngành/nhóm. |
| Danh mục tổ hợp | 280; 5 cột | Đọc nhưng không dùng ở cell 55 | `code`, `subject1`–`subject4` chưa đối chiếu với `score_blocks`; mất cơ hội kiểm tra tổ hợp hợp lệ và tạo đặc trưng môn học liên quan. |
| Trends topics | 3.579; 5 cột | Chỉ đếm `keyword_type` | `keyword`, `mid`, `title`, `type` chưa đối chiếu với query được chọn. |
| Trends keywords / queries | 927 / 879 | Keywords chỉ dùng `query_id`, `keyword`, `keyword_type`; queries chỉ dùng `status`, `nonzero_points` để báo cáo | Chưa kiểm tra `selection_reason`, `relevance_score`, `candidate_count`, `query_kind`, `stage_interest`, `geo`, `date_range` khi đánh giá chất lượng nối. |
| Trends timeline / annual | 240.846 / 20.217 | Dùng chuỗi tháng và trung bình/đỉnh/năm | `interest_sum` không dùng; `interest_season_peak` bị hiểu sai thành tháng đỉnh. Dữ liệu 2010–2025 sau lọc là 168.768 / 14.064 dòng. |
| Trends regions / related queries | 10.195 / 1.182 | Không đọc | Đây có thể là nguồn kiểm tra độ liên quan theo vùng và nghĩa của từ khóa. Không bắt buộc dùng làm feature, nhưng phải đánh giá có/không hữu ích. |

Chênh lệch điểm chuẩn thô → sạch là **46.205 dòng (31,3%)**. Trong dữ liệu thô có 8.173 dòng năm 2026 và 4.212 dòng thiếu năm; việc loại chúng khi giới hạn đến 2025 có thể hợp lý. Phần còn lại cần bảng đối soát theo từng bước: thiếu trường bắt buộc, trùng, ngoại lai IQR, mã ngành không hợp lệ. Script làm sạch hiện bỏ `score_formula` (32.022 giá trị không rỗng) và `score_is_converted_score` (147.513 giá trị không rỗng) trước khi notebook kiểm tra khả năng so sánh các thang điểm. `score_introtext` còn trong dữ liệu sạch nhưng không được notebook dùng để kiểm tra trường hợp thang 40/hệ số hoặc quy tắc xét tuyển.

**Kiểm kê cột điểm chuẩn:** `school_id`, `school_name`, `school_type`, `province_id`, `score_code`, `score_name`, `score_blocks`, `score_mark`, `score_year`, `score_admission_name` có đi vào đọc/biến đổi/phân tích. `school_short_name`, `province_name`, `score_introtext` đi qua làm sạch nhưng không được kiểm nghiệm trong notebook. Hai cột thô `score_formula`, `score_is_converted_score` bị loại trước notebook. Đề nghị lập bảng cho **mọi cột** gồm kiểu dữ liệu, tỷ lệ thiếu, số giá trị riêng, phân bố theo năm/phương thức, mục đích sử dụng hoặc lý do loại; cột không dùng vẫn phải được kiểm tra.

### Thuộc tính bị lọt hoặc biến dạng trong pipeline

1. **Sai số lượng tổ hợp (`num_blocks`)** — cell 55 tách `score_blocks` bằng dấu phẩy, trong khi script làm sạch ghi bằng dấu chấm phẩy. Kết quả thực chạy: **57.400/57.400 dòng có `num_blocks = 1`**. Có 32.468 dòng điểm chuẩn sạch thiếu `score_blocks`; giá trị thiếu cũng bị biến thành 1, che mất thiếu dữ liệu. Sửa thành tách `;`, giữ `NaN`/cờ thiếu và đối chiếu từng mã với bảng tổ hợp.
2. **Mất biến thiên của hai số lượng phương thức** — `num_methods_in_major` và `num_methods_in_school` được `groupby(...).nunique()` sau khi `df_thpt` chỉ còn một phương thức. Cả hai đều bằng **1 trên mọi dòng**. Trong toàn bộ dữ liệu sạch có 22.151 nhóm trường–mã ngành–năm chứa hơn một phương thức; cần tính từ toàn bộ bảng rồi nối vào tập mục tiêu. Cần xác nhận các phương thức đã được công bố trước mốc dự báo.
3. **Khóa lịch sử không duy nhất** — cell 55 nhóm theo `school_id, score_code` và `shift(1/2)` theo dòng. Trong 57.400 dòng THPT chỉ có 47.284 bộ `school_id, score_code, score_year`; **15.703 dòng** thuộc khóa trùng, **5.024 nhóm khóa trùng có nhiều điểm khác nhau**. Trong 48.491 lag1 không khuyết, **10.116 lag1 đến từ cùng năm**, 2.755 đến từ khoảng cách hơn một năm; chỉ 35.620 đến từ đúng năm trước. Vì vậy `cutoff_lag1`, `cutoff_lag2`, `cutoff_delta_prev`, `cutoff_roll_mean2` và `cutoff_delta` chưa mang nghĩa được mô tả. Cần bổ sung đơn vị tuyển sinh thật (tổ hợp/đợt/chương trình/cơ sở/phương thức nếu có) hoặc quy tắc tổng hợp có lý do nghiệp vụ, rồi dùng self-join với `score_year = t-1/t-2` và kiểm tra tính duy nhất.
4. **`school_trend_peak_month` không phải tháng** — cell 3 đổi tên `interest_season_peak` thành `peak_month`. Trong `clean_trends.py`, cột gốc là **trung bình `interest` của tháng 5–8**, có giá trị liên tục 0–96,25; không phải số tháng 1–12. `school_peak_intensity` và diễn giải Tier 3 về đỉnh tháng 7–8 vì thế chưa được kiểm chứng. Muốn tháng đỉnh phải tính `argmax` từ timeline theo query/năm, xử lý hòa điểm rõ ràng.
5. **Nhãn `admission_method_trend_lag10m` sai** — cell 55 đặt mốc tháng 8 năm T rồi trừ **4 tháng**, tức tháng 4 năm T; đây là lag 4 tháng. PACF lag 10 là một quan hệ khác. Đổi tên hoặc lấy đúng mốc lag 10 và kiểm nghiệm lại. Các lags khác cũng cần bảng `tại thời điểm nào → tháng dữ liệu nào → có sẵn khi dự báo không`.
6. **Ánh xạ ngành có nhiều nghĩa** — sau khi tách `score_codes`, có **923 mã** gắn với hơn một `major_group_name`, 321 mã gắn với hơn một `major_name`. `drop_duplicates` lấy dòng đầu tiên mà không kiểm tra xung đột; `group_trend_mean` và `major_trend_mean` có thể sai nghĩa. Cần khóa danh mục ổn định hơn, hoặc báo cáo/phê duyệt quy tắc giải xung đột.
7. **Điểm không hợp lệ chưa được lọc như ý định** — `cutoff_scores.py` ghi chú loại `score_mark <= 0` nhưng mã lại lọc `score_year > 0`. Dữ liệu sạch vẫn còn **1.313 dòng điểm ≤ 0** (dữ liệu thô giai đoạn 2010–2025 có 6.557 dòng như vậy). Phải xác định 0 là điểm thật, giá trị thiếu hay lỗi nhập trước khi sửa điều kiện và đo tác động tới từng phương thức.
8. **Trung bình Trends bị lặp trọng số query** — các cell vẽ chuỗi theo `keyword_type` và cell 55 nối timeline/annual với `trend_keywords` rồi lấy trung bình, nhưng có **28 cặp (`query_id`, `keyword_type`) lặp**, tạo thêm 32 dòng keyword cho cùng query/type. Một query có nhiều keyword được tính nhiều lần; phép nối annual 20.217 dòng thành 21.321 dòng. Cần `drop_duplicates(['query_id', 'keyword_type'])` trước khi tính trung bình nếu muốn mỗi query có trọng số bằng nhau, hoặc công bố trọng số theo keyword và kiểm nghiệm độ nhạy.

## 2. Phương pháp luận

### Những điểm hợp lý

- Tách khám phá dữ liệu, xây dựng đặc trưng, đánh giá đặc trưng và đề xuất mô hình là một trình tự dễ theo dõi.
- Đề cập zero-interest, thiếu ánh xạ, quán tính điểm chuẩn và chia train/validation theo năm là đúng hướng.
- Phương án baseline theo lịch sử và GBDT là các giả thuyết đáng thử, nhưng phải so sánh trên cùng tập test sau khi sửa dữ liệu.

### Những chỗ suy luận chưa đủ chặt

1. **Bài toán dự báo chưa có mốc thời gian cụ thể.** Notebook dùng trung bình, cực đại, YoY và tháng đỉnh của **cả năm T** để dự đoán điểm chuẩn năm T. Nếu mục tiêu là dự báo trước công bố điểm chuẩn tháng 8, các tháng sau mốc đó là thông tin tương lai. Cũng cần xác định `num_majors_in_school`, `num_schools_offering_major` và phương thức tuyển sinh có biết trước mốc ấy không. Mọi biến phải được cắt theo ngày dự báo; nên thí nghiệm các mốc như cuối tháng 3, 5, 7.
2. **Khảo sát PACF trên chuỗi trung bình của nhiều query không chứng minh lag hữu ích cho từng trường/ngành.** Các cell 18–50 gộp `interest` theo ngày rồi tính PACF trên một chuỗi trung bình; sau đó áp lag này cho từng thực thể. Tín hiệu của chuỗi gộp có thể phản ánh mùa vụ chung, số query có dữ liệu thay đổi, hoặc xu thế dài hạn. Cần kiểm tra tính dừng, độ phủ theo tháng, PACF theo nhóm/query và hiệu quả dự báo ngoài mẫu. Cell 13 dùng dãy `activity_weights` tự đặt để vẽ mùa vụ điểm chuẩn, không phải quan sát từ dữ liệu; phải ghi rõ là sơ đồ minh họa, không dùng làm bằng chứng thống kê.
3. **Các phép thống kê ở mục 4 là khám phá trên cùng tập dùng để chọn feature.** Cell 59 điền trung vị trên toàn bộ dữ liệu; cell 65 fit Extra Trees trên toàn bộ; cell 71 tính F-test trên toàn bộ; cell 73 chọn Tier từ đó. Năm test 2025 đã tác động lựa chọn đặc trưng và phép điền khuyết. Để có đánh giá không rò rỉ, mọi phép fit/impute/select phải nằm trong từng fold huấn luyện theo thời gian. Cell 75 nói target encoding K-fold=5; nếu làm K-fold ngẫu nhiên trong train sẽ lộ năm sau về năm trước — cần mã hóa theo năm tăng dần và smoothing chỉ từ quá khứ.
4. **Tương quan/F-test/MDI chưa chứng minh khả năng dự báo hay tác động riêng.** `f_regression` là kiểm định quan hệ tuyến tính đơn biến; p-value nhỏ trên các dòng lặp theo trường/năm không đồng nghĩa feature đóng góp độc lập. MDI chia importance giữa các biến liên quan và ưu tiên biến có nhiều ngưỡng. Polynomial cell 68 chỉ so tương quan đơn biến của tích với target, chưa chứng minh tăng hiệu năng. Cần ablation/Permutation importance trên validation theo năm, so sánh với baseline và khoảng bất định theo năm/trường.
5. **Các biến xu hướng vĩ mô có thể là proxy của năm.** `subject`, `subject_group`, `admission_method` được trung bình toàn bộ query của một loại theo năm rồi gán cùng giá trị cho mọi dòng năm đó; chưa nối với tổ hợp/môn/phương thức thực tế của dòng. Tương quan cao có thể chỉ phản ánh xu hướng năm và tăng cùng chiều với điểm chuẩn. Cần so với baseline có `year`, kiểm tra loại bỏ từng nhóm và xây tín hiệu liên quan đúng thực thể.
6. **Dữ liệu điểm chuẩn chưa cùng thang đo.** Notebook nói THPT thang 30, nhưng tập THPT sạch có **512 dòng `score_mark > 30`**, tối đa 34; các phương thức còn lại dùng thang khác nhau. Phải phân tầng theo phương thức, xác thực quy tắc chuyển đổi từ `score_formula`, `score_is_converted_score`, `score_introtext`, rồi mới tính MAE/RMSE hoặc gộp dữ liệu.
7. **Kết luận mô hình đi trước kiểm nghiệm.** Chưa có train/test và bảng MAE/RMSE của ba kiến trúc. Các ngưỡng MAE ≤0,75, RMSE ≤1,15, R² ≥0,85 ở cell 77 là mục tiêu đề xuất, không phải kết quả. Cell 73 nói một số feature “không cải thiện RMSE” nhưng notebook chưa tính RMSE. Khuyến nghị Two-Stage Hybrid chỉ nên là giả thuyết cho thử nghiệm.

## 3. Những điểm chưa thể khẳng định đúng/sai

| Nghi vấn | Vì sao chưa kết luận | Cách xác minh |
|---|---|---|
| 46.205 dòng bị loại từ dữ liệu thô có làm lệch tập nghiên cứu không? | Có năm 2026 và dòng thiếu năm, nhưng chưa có nhật ký số dòng theo từng điều kiện lọc, phương thức, trường. | Lập bảng waterfall từng bước làm sạch; so phân bố điểm/trường/năm trước–sau; xem mẫu dòng bị loại. |
| Một mã ngành xuất hiện nhiều lần cùng năm có phải các chương trình/đợt/tổ hợp hợp lệ? | CSV không có khóa chương trình/đợt rõ ràng; trùng khóa hiện tại không tự động là trùng bản ghi. | Lấy mẫu 5.024 nhóm có nhiều điểm, đối chiếu `score_name`, `score_blocks`, `score_introtext`, trang nguồn; quyết định đơn vị dự báo. |
| So sánh hoặc lấy trung bình Google Trends 0–100 giữa các query có hợp lệ không? | Google Trends chuẩn hóa theo truy vấn/khung thời gian; notebook chưa chứng minh điểm giữa query/đợt crawl đồng thang. | Kiểm tra `query_kind`, `geo`, `date_range`, quy trình crawl; thử từ khóa neo và độ nhạy với cách chuẩn hóa. |
| Kết quả xu hướng có ổn định theo vùng và nghĩa từ khóa không? | `trend_regions`, `trend_related_queries`, `relevance_score` và metadata chọn topic chưa được dùng để kiểm định. | Kiểm tra mẫu query có nhiều nghĩa, vùng ngoài mục tiêu, tín hiệu zero; so kết quả khi lọc theo độ liên quan. |
| Có nên dùng các phương thức ngoài THPT trong cùng mô hình? | Điểm không cùng thang và mục tiêu nghiệp vụ chưa nêu rõ. | Định nghĩa đầu ra: THPT riêng, từng phương thức riêng, hoặc điểm quy đổi có quy tắc nguồn; so độ phủ và chất lượng từng nhóm. |
| Tính mùa vụ/PACF và lợi ích Trends có bền qua thay đổi chính sách thi? | Chuỗi trung bình gộp 16 năm, chưa có phân tích theo giai đoạn hoặc test ngoài mẫu. | Kiểm tra từng giai đoạn, theo trường/ngành, chạy ablation trên validation 2022–2024 và test 2025. |

## 4. Các sai lệch khác cần sửa trong notebook

- Cell 7 tìm trạng thái `'VALID'`, nhưng `trend_queries.csv` hiện có `interest_only` = **679** và `success` = **200**, nên dòng “Query hợp lệ (VALID)” in 0. Query `nonzero_points == 0` là **168/879 = 19,1%**; diễn giải ở cell 8/75 ghi **56,7%** không khớp snapshot dữ liệu. `interest_only` không đồng nghĩa zero-interest.
- Cell 11 biểu đồ nói “theo phương thức xét tuyển”, nhưng thực tế chỉ vẽ THPT và học bạ; không có các phương thức còn lại. Nếu chỉ so hai nhóm, đổi tiêu đề và nêu thang điểm/độ phủ từng năm.
- Cell 59 `dropna(cutoff_lag1)` loại **8.909/57.400 dòng (15,5%)**, chính là nhiều ngành mới/chuỗi ngắn. Kết luận feature chỉ áp dụng cho tập có lịch sử; cần đánh giá riêng cold start và báo cáo sai lệch mẫu.
- `province_id` được đưa như số liên tục; mô hình tuyến tính sẽ giả định khoảng cách giữa mã tỉnh có ý nghĩa. `school_type_enc` được mô tả là **công lập/tư thục**, nhưng mã thực tế là **Đại học/Cao đẳng**; trong tập THPT chỉ có 2 dòng Cao đẳng. Cần sửa ý nghĩa và kiểm tra phương sai, không suy luận tầm quan trọng từ mã số.
- `warnings.filterwarnings('ignore')` che cảnh báo hữu ích; `statsmodels` thiếu khỏi `requirements.txt`; chưa có cell kiểm tra khóa duy nhất, phạm vi điểm, schema và thời điểm sẵn có của feature. Các con số cố định trong markdown có thể cũ so với CSV mới.

## 5. Quy trình kiểm nghiệm lại đề xuất

### P0 — Chốt dữ liệu và mục tiêu trước khi chọn feature

1. **Viết data contract:** một dòng là gì, khóa duy nhất là gì, dự báo cho phương thức nào, năm nào và vào ngày nào. Lưu phiên bản dữ liệu/commit và ngày crawl. Không trộn thang điểm khi chưa có quy tắc quy đổi kiểm chứng được.
2. **Kiểm kê đủ mọi thuộc tính:** với từng bảng raw và cleaned, xuất schema, kiểu, tỷ lệ thiếu, số giá trị riêng, phạm vi, phân bố theo năm/phương thức; đối chiếu tập cột raw → cleaned → notebook → candidate features. Ghi rõ cột bị loại và lý do. Với điểm chuẩn, tạo waterfall số dòng qua từng bước làm sạch, không chỉ so tổng trước/sau.
3. **Kiểm tra khóa và phép nối:** `validate='many_to_one'` cho join annual/query-year; phát hiện khóa target trùng, mã ngành nhiều nghĩa, keyword sau chuẩn hóa bị trùng; xuất mẫu xung đột để quyết định quy tắc giải. Kiểm tra số dòng trước/sau mỗi merge, tỷ lệ match theo loại keyword, năm và phương thức. Không để phép `drop_duplicates` tùy ý quyết định ánh xạ.
4. **Sửa phép tính:** tách `score_blocks` bằng `;`, xác thực với `score-blocks.csv`; tính số phương thức trên bảng đủ phương thức; tạo lag bằng khóa năm chính xác; tính tháng đỉnh từ timeline; sửa nhãn lag 4/10; giữ cờ thiếu cho mỗi nguồn Trends. Đặt `assert` cho miền giá trị (`num_blocks > 1` phải có nếu dữ liệu chứa nhiều tổ hợp; lag1 phải đúng `t-1`; `peak_month` thuộc 1–12).

### P1 — Chống rò rỉ và đánh giá lại phương pháp

5. **Lập bảng availability của từng feature:** ngày cuối dữ liệu được dùng phải không muộn hơn ngày dự báo. Tạo phiên bản feature theo mốc cuối tháng 3, 5, 7. Các chỉ số năm T phải tính từ phần năm đã quan sát; mọi thống kê điền khuyết, chuẩn hóa, chọn feature và mã hóa target chỉ fit từ quá khứ trong từng fold.
6. **Đánh giá theo expanding window:** dùng 2022–2024 để chọn cấu hình và tập feature, khóa 2025 làm test cuối. Giữ các dòng cùng trường/ngành/năm trong cùng phần chia. Báo cáo theo năm, trường, nhóm ngành, dải điểm, có/không có lag, có/không có Trends. So các baseline: điểm năm trước hợp lệ, trung vị cùng trường/ngành, Ridge; sau đó GBDT và Two-Stage trên cùng dữ liệu. So sánh MAE/RMSE/hit rate và độ phủ, kèm khoảng tin cậy theo bootstrap nhóm trường hoặc năm.
7. **Ablation có kiểm soát:** thêm lần lượt lịch sử → cấu trúc → Trends đã cắt theo mốc → lag tháng; đo mức cải thiện trên validation/test. Dùng permutation importance trên validation, không xếp Tier theo tương quan/F-test trên toàn bộ 2010–2025. Kiểm tra trường hợp chỉ có vài năm dữ liệu và query zero-interest riêng biệt.

### Tiêu chí chấp nhận tối thiểu

- Có bảng đối soát **100% cột** raw/cleaned và lý do dùng/loại; tổng số dòng qua các bước được giải thích.
- Không còn feature hằng do lỗi xử lý; `num_blocks`/số phương thức/peak month đúng nghĩa; các join bảo toàn số dòng dự kiến.
- Với `cutoff_lag1/2`, không có trường hợp lấy cùng năm hoặc năm sau; mọi giá trị có chứng cứ đúng `t-1/t-2` theo khóa đã chốt.
- Mỗi feature có mốc sẵn có không sau ngày dự báo; test 2025 chưa dùng để điền khuyết, chọn feature hoặc chỉnh mô hình.
- Kết luận về Trends/Tier/mô hình chỉ giữ lại nếu cải thiện chỉ số ngoài mẫu so với baseline, có bảng kết quả và độ phủ theo nhóm.

**Vị trí đối chiếu:** notebook cell 3, 7, 11, 13, 18–50, 54–55, 59, 65, 68, 71, 73, 75–78; `scripts-processing/unit-scripts/cutoff_scores.py` (bỏ cột, chuẩn hóa `score_blocks`, lọc/IQR); `scripts-processing/unit-scripts/clean_trends.py` (định nghĩa `interest_season_peak`); các CSV tại `data-raw/` và `data-cleaned/`.

## Phụ lục: checklist toàn bộ thuộc tính nguồn

Các nhóm dưới đây liệt kê **mọi cột CSV** để lần kiểm nghiệm tiếp theo không bỏ sót. “Chưa dùng” không đồng nghĩa bắt buộc đưa vào mô hình; nó đòi hỏi kiểm tra chất lượng và ghi lý do loại. Với mỗi cột, cần lưu `dtype`, số/tỷ lệ null, số giá trị riêng, miền giá trị hoặc ví dụ sai, phân bố theo năm/nguồn, phép biến đổi, và tình trạng sau mỗi bước nối.

| Nguồn | Cột hiện có | Tình trạng trong notebook |
|---|---|---|
| `data-raw/admission-cutoff-score/cutoff-scores.csv` | `school_id`, `school_name`, `school_type`, `school_short_name`, `province_id`, `province_name`, `score_code`, `score_name`, `score_blocks`, `score_mark`, `score_year`, `score_introtext`, `score_formula`, `score_is_converted_score`, `score_admission_name` | Hai cột cuối trước `score_admission_name` là `score_formula`, `score_is_converted_score`: bị bỏ ở script sạch. Các cột còn lại thành 13 cột cleaned; ba cột `school_short_name`, `province_name`, `score_introtext` không được phân tích. |
| `majors.csv` | `major_group_id`, `major_group_name`, `major_id`, `major_name`, `major_description`, `score_codes` | Dùng tên nhóm, tên ngành, danh sách mã; ID/mô tả chưa kiểm tra. |
| `score-blocks.csv` | `code`, `subject1`, `subject2`, `subject3`, `subject4` | Đọc file nhưng chưa kiểm tra hay nối cột nào. |
| `trend_topics.csv` | `keyword`, `keyword_type`, `mid`, `title`, `type` | Chỉ dùng `keyword_type` để đếm. |
| `trend_keywords.csv` | `query_id`, `keyword`, `keyword_type`, `selected_mid`, `selected_title`, `relevance_score`, `selection_reason`, `candidate_count` | Dùng ba cột đầu để nối/tổng hợp; năm cột còn lại chưa kiểm tra chất lượng ánh xạ. |
| `trend_queries.csv` | `query_id`, `query`, `query_kind`, `mid`, `title`, `type`, `selection_score`, `status`, `stage_interest`, `stage_enrichment`, `enrichment_skip_reason`, `nonzero_points`, `average_interest`, `max_interest`, `geo`, `date_range` | Chỉ dùng `status`, `nonzero_points` trong phần mô tả. Cần kiểm tra `query_id` với bảng con, `geo`, thời gian và metadata chọn query. |
| `trend_timeline.csv` | `query_id`, `date`, `year`, `month`, `interest` | Dùng `query_id`, `date`, `interest`; hai cột lịch cần đối chiếu với `date` và kiểm tra đủ 12 tháng/năm. |
| `trend_annual.csv` | `query_id`, `year`, `interest_mean`, `interest_max`, `interest_sum`, `interest_season_peak`, `nonzero_months` | Dùng tất cả trừ `interest_sum`; `interest_season_peak` bị đổi tên sai. Cần đối soát phép tính với timeline. |
| `trend_regions.csv` | `query_id`, `region`, `rank`, `value` | Chưa đọc; cần xét tính hữu ích cho trường/tỉnh. |
| `trend_related_queries.csv` | `query_id`, `query_type`, `related_query`, `rank`, `value`, `is_breakout`, `metric_type` | Chưa đọc; cần xét chất lượng ngữ nghĩa của query. |

`data-raw/google-trends/trends.json` gồm 879 object, ngoài dữ liệu đã tách còn có `errors`, `keyword_metadata.selected_type`, `interest_over_time.data_source`, `interest_over_time.request_terms`, `interest_over_time.collected_at`, `interest_by_region.data_source`, `commonly_searched_queries.data_source`. Các trường này chưa được giữ đầy đủ trong CSV sạch và chưa được notebook kiểm tra; nên lưu/đối soát metadata nguồn và thời điểm thu thập trước khi diễn giải quan hệ theo thời gian. Hai bảng `majors.csv`, `score-blocks.csv` và `trend_topics.csv` ở raw và cleaned có cùng số dòng; vẫn cần so hash/nội dung cột, không suy ra giống nhau chỉ từ số dòng.
