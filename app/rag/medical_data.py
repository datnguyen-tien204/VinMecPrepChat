"""
app/rag/medical_data.py – Dữ liệu hạt giống cho Vinmec RAG.

Gồm 3 phần:
  SPECIALTIES  – 20 chuyên khoa Vinmec phổ biến
  PROCEDURES   – 30+ xét nghiệm / thủ thuật / kỹ thuật chẩn đoán
  DOCUMENTS    – FAQ, lưu ý chung khi đến Vinmec

Rule mapping: specialty/procedure → fasting, documents, booking, duration
Đây là nguồn sự thật duy nhất (source of truth) cho checklist RAG.
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  SPECIALTIES  (20 chuyên khoa)
# ═══════════════════════════════════════════════════════════════════════════════
SPECIALTIES = [
    {
        "name": "Nội khoa tổng quát",
        "name_en": "General Internal Medicine",
        "department": "Nội",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD hoặc hộ chiếu", "Thẻ BHYT (nếu có)", "Kết quả xét nghiệm / phim cũ (nếu có)"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Nên đặt lịch trước để tránh chờ lâu. Mang theo toa thuốc đang dùng nếu có.",
        "tags": ["nội khoa", "khám tổng quát", "nội", "general", "internal medicine"],
    },
    {
        "name": "Tim mạch",
        "name_en": "Cardiology",
        "department": "Nội Tim Mạch",
        "fasting": "partial",
        "fasting_hours": 4,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "ECG, siêu âm tim cũ nếu có", "Danh sách thuốc đang dùng"]',
        "booking_required": True,
        "estimated_duration_min": 90,
        "notes": "Nhịn ăn 4 tiếng nếu bác sĩ yêu cầu xét nghiệm máu hay siêu âm tim mạch. Không dừng thuốc tim đột ngột.",
        "tags": ["tim mạch", "tim", "cardiology", "nhịp tim", "huyết áp", "heart"],
    },
    {
        "name": "Sản phụ khoa",
        "name_en": "Obstetrics & Gynecology",
        "department": "Sản",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Sổ khám thai / hồ sơ thai sản (nếu đang mang thai)"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Siêu âm thai nên uống nước nhiều trước 30 phút để bàng quang đầy (3 tháng đầu). Mang sổ khám thai.",
        "tags": ["sản", "phụ khoa", "thai sản", "mang thai", "obstetrics", "gynecology", "khám phụ khoa"],
    },
    {
        "name": "Nhi khoa",
        "name_en": "Pediatrics",
        "department": "Nhi",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD của cha/mẹ", "Giấy khai sinh hoặc hộ khẩu của trẻ", "Sổ tiêm chủng", "Thẻ BHYT trẻ em (nếu có)"]',
        "booking_required": True,
        "estimated_duration_min": 45,
        "notes": "Mang theo sổ tiêm chủng và tóm tắt bệnh lý trẻ. Không cho trẻ ăn no ngay trước khi lấy máu.",
        "tags": ["nhi", "trẻ em", "pediatrics", "nhi khoa", "children", "bé"],
    },
    {
        "name": "Xương khớp – Cơ xương khớp",
        "name_en": "Orthopedics & Rheumatology",
        "department": "Ngoại Cơ Xương Khớp",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Phim X-quang, MRI, CT cũ nếu có", "Kết quả xét nghiệm viêm khớp nếu có"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Mặc quần áo rộng, dễ cử động để bác sĩ khám. Mang phim X-quang nếu đã chụp trước đó.",
        "tags": ["xương khớp", "cơ xương", "orthopedics", "khớp", "đau lưng", "thoát vị đĩa đệm"],
    },
    {
        "name": "Thần kinh",
        "name_en": "Neurology",
        "department": "Nội Thần Kinh",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Kết quả MRI/CT sọ não cũ", "Danh sách thuốc đang dùng"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Ghi lại tần suất, thời gian, đặc điểm triệu chứng (đau đầu, chóng mặt, động kinh…) trước khi đến.",
        "tags": ["thần kinh", "neurology", "đau đầu", "đột quỵ", "chóng mặt", "động kinh", "mất ngủ"],
    },
    {
        "name": "Tiêu hoá – Gan mật",
        "name_en": "Gastroenterology & Hepatology",
        "department": "Nội Tiêu Hoá",
        "fasting": "required",
        "fasting_hours": 8,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Kết quả nội soi, siêu âm bụng cũ", "Kết quả xét nghiệm máu (AST, ALT, HBsAg…) nếu có"]',
        "booking_required": True,
        "estimated_duration_min": 90,
        "notes": "Nhịn ăn 8 tiếng nếu cần nội soi hoặc siêu âm bụng. Thông báo tiền sử dị ứng thuốc.",
        "tags": ["tiêu hoá", "gan", "mật", "gastroenterology", "nội soi", "dạ dày", "đại tràng", "viêm gan"],
    },
    {
        "name": "Nội tiết – Đái tháo đường",
        "name_en": "Endocrinology & Diabetes",
        "department": "Nội Tiết",
        "fasting": "required",
        "fasting_hours": 8,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Sổ theo dõi đường huyết tại nhà", "Danh sách thuốc đang dùng (insulin, metformin…)"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Nhịn ăn 8 tiếng để xét nghiệm đường huyết lúc đói (FPG) chính xác. Không tiêm insulin sáng đó nếu chưa được bác sĩ hướng dẫn.",
        "tags": ["nội tiết", "đái tháo đường", "tiểu đường", "endocrinology", "tuyến giáp", "insulin", "hormone"],
    },
    {
        "name": "Hô hấp – Phổi",
        "name_en": "Pulmonology",
        "department": "Nội Hô Hấp",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Phim X-quang phổi cũ", "Kết quả đo chức năng hô hấp (spirometry) nếu có"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Không hút thuốc ít nhất 4 tiếng trước khám. Mặc quần áo rộng để đo chức năng hô hấp.",
        "tags": ["hô hấp", "phổi", "pulmonology", "hen suyễn", "COPD", "viêm phổi", "ho", "khó thở"],
    },
    {
        "name": "Thận – Tiết niệu",
        "name_en": "Nephrology & Urology",
        "department": "Nội Thận – Tiết Niệu",
        "fasting": "partial",
        "fasting_hours": 4,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Kết quả xét nghiệm nước tiểu, creatinine, eGFR cũ", "Phim siêu âm thận cũ"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Nhịn ăn 4 tiếng nếu cần xét nghiệm máu. Thu thập mẫu nước tiểu buổi sáng (giữa dòng) trước khi đến nếu bác sĩ yêu cầu.",
        "tags": ["thận", "tiết niệu", "nephrology", "urology", "sỏi thận", "viêm thận", "tiểu buốt"],
    },
    {
        "name": "Ung bướu",
        "name_en": "Oncology",
        "department": "Ung Bướu",
        "fasting": "partial",
        "fasting_hours": 4,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Hồ sơ ung thư (sinh thiết, PET/CT, MRI cũ)", "Phác đồ hóa trị / xạ trị đang thực hiện"]',
        "booking_required": True,
        "estimated_duration_min": 120,
        "notes": "Mang đầy đủ hồ sơ bệnh lý. Thông báo nếu đang trong quá trình hóa trị / xạ trị / dùng thuốc nhắm trúng đích.",
        "tags": ["ung bướu", "ung thư", "oncology", "hóa trị", "xạ trị", "khối u", "sinh thiết"],
    },
    {
        "name": "Da liễu",
        "name_en": "Dermatology",
        "department": "Da Liễu",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)"]',
        "booking_required": True,
        "estimated_duration_min": 30,
        "notes": "Không bôi thuốc / kem lên vùng da tổn thương trước khi đến. Chụp ảnh tổn thương tại nhà để theo dõi.",
        "tags": ["da liễu", "da", "dermatology", "mụn", "dị ứng da", "viêm da", "nấm da"],
    },
    {
        "name": "Mắt – Nhãn khoa",
        "name_en": "Ophthalmology",
        "department": "Mắt",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Kính đang đeo (nếu có)", "Đơn kính cũ"]',
        "booking_required": True,
        "estimated_duration_min": 45,
        "notes": "Không đeo kính áp tròng ít nhất 2 ngày trước đo khúc xạ. Mang theo kính đang dùng.",
        "tags": ["mắt", "nhãn khoa", "ophthalmology", "cận thị", "đục thủy tinh thể", "glaucoma", "kính"],
    },
    {
        "name": "Tai mũi họng",
        "name_en": "ENT – Otolaryngology",
        "department": "Tai Mũi Họng",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Kết quả đo thính lực cũ (nếu có)"]',
        "booking_required": True,
        "estimated_duration_min": 30,
        "notes": "Không vệ sinh tai sâu bằng tăm bông trước khi khám. Thông báo tiền sử phẫu thuật tai mũi họng.",
        "tags": ["tai mũi họng", "ENT", "otolaryngology", "ù tai", "viêm xoang", "amidan", "nghe kém"],
    },
    {
        "name": "Khám sức khoẻ tổng quát",
        "name_en": "Comprehensive Health Check-up",
        "department": "Khám Sức Khoẻ",
        "fasting": "required",
        "fasting_hours": 10,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Kết quả khám sức khoẻ gần nhất (nếu có)"]',
        "booking_required": True,
        "estimated_duration_min": 180,
        "notes": "Nhịn ăn ít nhất 10 tiếng (thường là qua đêm). Uống nước lọc bình thường được. Không uống rượu bia 24 tiếng trước. Mặc đồ thoải mái.",
        "tags": ["khám tổng quát", "kiểm tra sức khoẻ", "health check", "tổng quát", "định kỳ"],
    },
    {
        "name": "Tâm thần – Sức khoẻ tâm thần",
        "name_en": "Psychiatry & Mental Health",
        "department": "Tâm Thần",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Danh sách thuốc tâm thần đang dùng", "Hồ sơ bệnh án tâm thần cũ (nếu có)"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Không dừng thuốc tâm thần đột ngột. Người thân nên đi cùng để cung cấp thêm thông tin.",
        "tags": ["tâm thần", "sức khoẻ tâm thần", "psychiatry", "trầm cảm", "lo âu", "mất ngủ", "tâm lý"],
    },
    {
        "name": "Phẫu thuật – Ngoại khoa",
        "name_en": "Surgery",
        "department": "Ngoại",
        "fasting": "required",
        "fasting_hours": 8,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Kết quả xét nghiệm tiền phẫu (xét nghiệm máu, ECG, X-quang phổi)", "Hồ sơ chỉ định phẫu thuật"]',
        "booking_required": True,
        "estimated_duration_min": 120,
        "notes": "Nhịn ăn và nước ít nhất 8 tiếng trước phẫu thuật hoặc thủ thuật có gây mê. Ngừng thuốc chống đông theo hướng dẫn bác sĩ.",
        "tags": ["phẫu thuật", "ngoại khoa", "surgery", "mổ", "gây mê", "tiền phẫu"],
    },
    {
        "name": "Sơ sinh – Chuyên khoa sơ sinh",
        "name_en": "Neonatology",
        "department": "Nhi Sơ Sinh",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD của cha/mẹ", "Giấy khai sinh (nếu đã có)", "Phiếu xuất viện sơ sinh", "Sổ tiêm chủng"]',
        "booking_required": True,
        "estimated_duration_min": 45,
        "notes": "Mang theo toàn bộ hồ sơ xuất viện sơ sinh. Chuẩn bị tã, bình sữa cho bé trong thời gian chờ.",
        "tags": ["sơ sinh", "neonatal", "nhi sơ sinh", "trẻ sơ sinh", "bú mẹ"],
    },
    {
        "name": "Phục hồi chức năng",
        "name_en": "Physical Medicine & Rehabilitation",
        "department": "Phục Hồi Chức Năng",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '["CMND/CCCD", "Thẻ BHYT (nếu có)", "Hồ sơ chẩn đoán bệnh lý cần phục hồi", "Phim X-quang / MRI liên quan"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": "Mặc quần áo thoải mái, dễ cử động. Mang phim ảnh chẩn đoán liên quan.",
        "tags": ["phục hồi chức năng", "vật lý trị liệu", "rehabilitation", "đột quỵ", "chấn thương", "vật lý"],
    },
    {
        "name": "Xét nghiệm máu tổng quát",
        "name_en": "Complete Blood Count & Biochemistry",
        "department": "Xét Nghiệm",
        "fasting": "required",
        "fasting_hours": 8,
        "documents": '["CMND/CCCD", "Phiếu chỉ định xét nghiệm của bác sĩ"]',
        "booking_required": False,
        "estimated_duration_min": 30,
        "notes": "Nhịn ăn tối thiểu 8 tiếng (10-12 tiếng tốt hơn). Uống nước lọc vẫn được. Nên lấy máu buổi sáng sớm.",
        "tags": ["xét nghiệm máu", "blood test", "CBC", "sinh hoá máu", "lipid", "glucose", "lấy máu"],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  PROCEDURES  (30 xét nghiệm / thủ thuật)
# ═══════════════════════════════════════════════════════════════════════════════
PROCEDURES = [
    # ── Xét nghiệm máu ───────────────────────────────────────────────────────
    {
        "name": "Xét nghiệm đường huyết lúc đói (FPG)",
        "name_en": "Fasting Plasma Glucose",
        "procedure_type": "lab",
        "fasting": "required",
        "fasting_hours": 8,
        "preparation": "Nhịn ăn ít nhất 8 tiếng. Uống nước lọc được. Không uống cà phê, trà, nước trái cây.",
        "duration_min": 15,
        "contraindications": "Không áp dụng cho trường hợp hạ đường huyết cấp.",
        "notes": "Lấy máu buổi sáng sớm cho kết quả chính xác nhất. FPG ≥ 7.0 mmol/L → nguy cơ tiểu đường.",
        "tags": ["đường huyết", "FPG", "tiểu đường", "glucose", "nhịn ăn", "xét nghiệm máu"],
    },
    {
        "name": "Xét nghiệm mỡ máu (Lipid profile)",
        "name_en": "Lipid Panel",
        "procedure_type": "lab",
        "fasting": "required",
        "fasting_hours": 10,
        "preparation": "Nhịn ăn 10-12 tiếng. Không uống rượu bia 24 tiếng trước. Ăn uống bình thường 2 tuần trước (không ăn kiêng đột ngột).",
        "duration_min": 15,
        "contraindications": "Không có chống chỉ định đặc biệt.",
        "notes": "Kiểm tra LDL, HDL, triglycerides, total cholesterol. Kết quả phụ thuộc chế độ ăn.",
        "tags": ["mỡ máu", "lipid", "cholesterol", "LDL", "HDL", "triglycerides", "nhịn ăn"],
    },
    {
        "name": "Xét nghiệm HbA1c",
        "name_en": "Glycated Hemoglobin (HbA1c)",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không cần nhịn ăn. Phản ánh đường huyết trung bình 3 tháng qua.",
        "duration_min": 15,
        "contraindications": "Kết quả có thể không chính xác nếu có bệnh hemoglobin hoặc thiếu máu nặng.",
        "notes": "HbA1c ≥ 6.5% → chẩn đoán tiểu đường. Không cần nhịn ăn trước.",
        "tags": ["HbA1c", "tiểu đường", "đường huyết", "xét nghiệm máu", "không nhịn ăn"],
    },
    {
        "name": "Xét nghiệm chức năng gan (AST, ALT, GGT, Bilirubin)",
        "name_en": "Liver Function Tests (LFT)",
        "procedure_type": "lab",
        "fasting": "required",
        "fasting_hours": 8,
        "preparation": "Nhịn ăn 8 tiếng. Không uống rượu bia 48 tiếng trước vì có thể tăng giả AST/ALT.",
        "duration_min": 15,
        "contraindications": "Không có chống chỉ định đặc biệt.",
        "notes": "Đánh giá sức khoẻ gan. ALT tăng cao gợi ý tổn thương tế bào gan.",
        "tags": ["gan", "AST", "ALT", "GGT", "bilirubin", "chức năng gan", "viêm gan"],
    },
    {
        "name": "Xét nghiệm chức năng thận (Creatinine, eGFR, Urea)",
        "name_en": "Renal Function Tests",
        "procedure_type": "lab",
        "fasting": "partial",
        "fasting_hours": 4,
        "preparation": "Nhịn ăn nhẹ 4 tiếng. Uống đủ nước (không mất nước). Không ăn nhiều thịt đỏ buổi tối trước.",
        "duration_min": 15,
        "contraindications": "Không có chống chỉ định đặc biệt.",
        "notes": "eGFR < 60 ml/min/1.73m² → suy thận mạn độ 3+.",
        "tags": ["thận", "creatinine", "eGFR", "urea", "suy thận", "chức năng thận"],
    },
    {
        "name": "Xét nghiệm tổng phân tích tế bào máu (CBC)",
        "name_en": "Complete Blood Count (CBC)",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không cần nhịn ăn. Uống đủ nước để tránh kết quả sai do cô đặc máu.",
        "duration_min": 15,
        "contraindications": "Không có.",
        "notes": "Phát hiện thiếu máu, nhiễm trùng, bệnh máu. Có thể làm bất kỳ lúc nào.",
        "tags": ["CBC", "huyết đồ", "hemoglobin", "bạch cầu", "tiểu cầu", "thiếu máu"],
    },
    {
        "name": "Xét nghiệm TSH – Chức năng tuyến giáp",
        "name_en": "Thyroid Function Test (TSH, FT3, FT4)",
        "procedure_type": "lab",
        "fasting": "partial",
        "fasting_hours": 4,
        "preparation": "Nhịn ăn nhẹ 4 tiếng. Uống thuốc tuyến giáp SAU khi lấy máu (nếu đang dùng levothyroxine).",
        "duration_min": 15,
        "contraindications": "Kết quả TSH bị ảnh hưởng bởi thuốc tuyến giáp. Nên lấy máu buổi sáng trước khi uống thuốc.",
        "notes": "TSH thấp → cường giáp. TSH cao → suy giáp.",
        "tags": ["tuyến giáp", "TSH", "FT3", "FT4", "cường giáp", "suy giáp", "hormone giáp"],
    },
    {
        "name": "Xét nghiệm nước tiểu tổng quát",
        "name_en": "Urinalysis (UA)",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Thu thập nước tiểu giữa dòng buổi sáng sớm (bỏ 1-2 giây đầu, lấy giữa dòng). Không lấy trong 24h sau quan hệ tình dục.",
        "duration_min": 20,
        "contraindications": "Tránh lấy mẫu khi đang kỳ kinh nguyệt.",
        "notes": "Phát hiện nhiễm trùng tiểu, protein niệu, đường niệu, hồng cầu niệu.",
        "tags": ["nước tiểu", "urinalysis", "UA", "nhiễm trùng tiểu", "protein niệu", "tiểu buốt"],
    },
    # ── Chẩn đoán hình ảnh ──────────────────────────────────────────────────
    {
        "name": "Siêu âm ổ bụng tổng quát",
        "name_en": "Abdominal Ultrasound",
        "procedure_type": "imaging",
        "fasting": "required",
        "fasting_hours": 6,
        "preparation": "Nhịn ăn ít nhất 6 tiếng. Uống 4-6 ly nước lọc 1 tiếng trước để bàng quang đầy (nếu siêu âm cả vùng tiểu khung).",
        "duration_min": 20,
        "contraindications": "Không có chống chỉ định tuyệt đối.",
        "notes": "Kiểm tra gan, túi mật, tụy, lách, thận. Bàng quang đầy giúp nhìn rõ hơn.",
        "tags": ["siêu âm bụng", "abdominal ultrasound", "gan", "túi mật", "nhịn ăn", "siêu âm"],
    },
    {
        "name": "Siêu âm tim (Echocardiography)",
        "name_en": "Echocardiography (Echo)",
        "procedure_type": "imaging",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không cần nhịn ăn. Mặc quần áo rộng, dễ cởi phần ngực.",
        "duration_min": 30,
        "contraindications": "Không có.",
        "notes": "Đánh giá cấu trúc và chức năng tim. Không đau, không xâm lấn.",
        "tags": ["siêu âm tim", "echocardiography", "tim", "van tim", "chức năng tim"],
    },
    {
        "name": "X-quang ngực thẳng (Chest X-ray)",
        "name_en": "Chest X-ray (CXR)",
        "procedure_type": "imaging",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Tháo đồ trang sức kim loại, áo có dây kim loại. Thông báo nếu đang mang thai.",
        "duration_min": 10,
        "contraindications": "Phụ nữ mang thai (nếu không cấp thiết).",
        "notes": "Phát hiện viêm phổi, tràn khí màng phổi, tim phình to, lao phổi.",
        "tags": ["X-quang phổi", "chest X-ray", "CXR", "phổi", "lao", "viêm phổi"],
    },
    {
        "name": "CT Scan não",
        "name_en": "Brain CT Scan",
        "procedure_type": "imaging",
        "fasting": "partial",
        "fasting_hours": 4,
        "preparation": "Nhịn ăn 4 tiếng nếu dùng thuốc cản quang. Tháo toàn bộ đồ kim loại. Thông báo tiền sử dị ứng iốt/thuốc cản quang.",
        "duration_min": 20,
        "contraindications": "Dị ứng thuốc cản quang, suy thận nặng (nếu cần cản quang), mang thai.",
        "notes": "Phát hiện xuất huyết não, nhồi máu não, khối u. CT không cản quang không cần nhịn ăn.",
        "tags": ["CT não", "brain CT", "đột quỵ", "xuất huyết não", "cản quang", "CT scan"],
    },
    {
        "name": "MRI Cột sống",
        "name_en": "Spine MRI",
        "procedure_type": "imaging",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Tháo toàn bộ kim loại (đồng hồ, khuyên, kẹp tóc). Thông báo nếu có vật cấy ghép kim loại (stent, đinh vít).",
        "duration_min": 45,
        "contraindications": "Máy tạo nhịp tim, implant điện tử, mảnh kim loại trong cơ thể, sợ không gian kín.",
        "notes": "Không đau. Cần nằm yên trong máy khoảng 30-45 phút. Thông báo trước nếu sợ không gian kín.",
        "tags": ["MRI cột sống", "spine MRI", "thoát vị đĩa đệm", "đau lưng", "cột sống"],
    },
    {
        "name": "Điện tâm đồ (ECG/EKG)",
        "name_en": "Electrocardiogram (ECG)",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Mặc áo dễ cởi phần ngực. Không bôi kem dưỡng da vùng ngực và chân tay.",
        "duration_min": 10,
        "contraindications": "Không có.",
        "notes": "Ghi lại điện tim 12 chuyển đạo. Phát hiện rối loạn nhịp, nhồi máu cơ tim.",
        "tags": ["ECG", "EKG", "điện tâm đồ", "nhịp tim", "tim mạch", "rối loạn nhịp"],
    },
    {
        "name": "Nội soi dạ dày – tá tràng",
        "name_en": "Upper GI Endoscopy (Gastroscopy)",
        "procedure_type": "procedure",
        "fasting": "required",
        "fasting_hours": 8,
        "preparation": "Nhịn ăn ít nhất 8 tiếng (nhịn nước 4 tiếng). Ngừng thuốc aspirin/NSAIDs 7 ngày trước nếu bác sĩ yêu cầu. Có thể gây mê ngắn.",
        "duration_min": 30,
        "contraindications": "Rối loạn đông máu nặng, nghi thủng dạ dày.",
        "notes": "Nên đưa người thân đi cùng nếu dùng an thần. Không lái xe sau khi gây mê.",
        "tags": ["nội soi dạ dày", "gastroscopy", "dạ dày", "loét dạ dày", "HP", "nhịn ăn"],
    },
    {
        "name": "Nội soi đại tràng",
        "name_en": "Colonoscopy",
        "procedure_type": "procedure",
        "fasting": "required",
        "fasting_hours": 24,
        "preparation": "Chế độ ăn lỏng 1-2 ngày trước. Uống thuốc xổ theo hướng dẫn buổi tối hôm trước. Nhịn hoàn toàn buổi sáng hôm làm.",
        "duration_min": 45,
        "contraindications": "Nghi thủng đại tràng, viêm đại tràng cấp nặng.",
        "notes": "Cần người thân đưa về vì dùng an thần. Chuẩn bị kỹ ruột là yếu tố quyết định chất lượng soi.",
        "tags": ["nội soi đại tràng", "colonoscopy", "ung thư đại tràng", "polyp", "đại tràng"],
    },
    {
        "name": "Siêu âm thai",
        "name_en": "Obstetric Ultrasound",
        "procedure_type": "imaging",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "3 tháng đầu: uống 4-6 ly nước lọc 30-60 phút trước và không đi tiểu (bàng quang đầy). Tam cá nguyệt 2-3: không cần đặc biệt.",
        "duration_min": 20,
        "contraindications": "Không có.",
        "notes": "Mang sổ khám thai. Kiểm tra phát triển thai nhi, nhau thai, nước ối.",
        "tags": ["siêu âm thai", "obstetric ultrasound", "thai nhi", "mang thai", "sản khoa"],
    },
    {
        "name": "Đo loãng xương (Densitometry – DXA)",
        "name_en": "Bone Density Scan (DXA)",
        "procedure_type": "imaging",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không uống canxi 24 tiếng trước. Mặc quần áo không có kim loại.",
        "duration_min": 20,
        "contraindications": "Mang thai.",
        "notes": "Đo mật độ xương cột sống và cổ xương đùi. T-score ≤ -2.5 → loãng xương.",
        "tags": ["loãng xương", "DXA", "mật độ xương", "osteoporosis", "canxi"],
    },
    {
        "name": "Holter ECG 24 giờ",
        "name_en": "24-hour Holter Monitor",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Tắm trước khi đến. Không bôi kem/dầu dưỡng da vùng ngực. Mặc áo rộng.",
        "duration_min": 30,
        "contraindications": "Không có.",
        "notes": "Đeo máy 24 tiếng. Ghi nhật ký triệu chứng. Không tắm khi đang đeo.",
        "tags": ["Holter ECG", "nhịp tim 24h", "rối loạn nhịp", "hồi hộp", "tim mạch"],
    },
    {
        "name": "Đo huyết áp 24 giờ (ABPM)",
        "name_en": "Ambulatory Blood Pressure Monitoring (ABPM)",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Sinh hoạt bình thường. Mặc áo rộng tay. Giữ tay thẳng khi máy bơm.",
        "duration_min": 30,
        "contraindications": "Không có.",
        "notes": "Đo mỗi 15-30 phút trong 24 tiếng. Phát hiện tăng huyết áp áo choàng trắng / tăng huyết áp ẩn.",
        "tags": ["huyết áp 24h", "ABPM", "tăng huyết áp", "hypertension"],
    },
    # ── Sản khoa ─────────────────────────────────────────────────────────────
    {
        "name": "Xét nghiệm Double Test / Triple Test",
        "name_en": "First/Second Trimester Screening",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không cần nhịn ăn. Kết hợp với siêu âm đo độ mờ da gáy (tuần 11-13).",
        "duration_min": 30,
        "contraindications": "Không có.",
        "notes": "Tầm soát dị tật nhiễm sắc thể (Down syndrome, Edwards). Làm tuần 11-13 (Double Test) hoặc tuần 15-20 (Triple Test).",
        "tags": ["Double Test", "Triple Test", "Down syndrome", "tầm soát dị tật", "thai sản"],
    },
    {
        "name": "Xét nghiệm Pap Smear (Phết tế bào cổ tử cung)",
        "name_en": "Pap Smear / Cervical Cytology",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không quan hệ tình dục 48 tiếng trước. Không dùng thuốc âm đạo 48 tiếng trước. Không làm khi đang kỳ kinh.",
        "duration_min": 15,
        "contraindications": "Đang kỳ kinh nguyệt.",
        "notes": "Tầm soát ung thư cổ tử cung. Phụ nữ ≥ 21 tuổi nên làm 3 năm/lần.",
        "tags": ["Pap smear", "cổ tử cung", "ung thư cổ tử cung", "HPV", "phụ khoa"],
    },
    # ── Xét nghiệm đặc thù ──────────────────────────────────────────────────
    {
        "name": "Xét nghiệm HIV",
        "name_en": "HIV Test",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không cần chuẩn bị đặc biệt. Tư vấn trước và sau xét nghiệm.",
        "duration_min": 20,
        "contraindications": "Không có.",
        "notes": "Kết quả bảo mật. Cần tư vấn trước/sau test. Giai đoạn cửa sổ: 6 tuần đến 3 tháng.",
        "tags": ["HIV", "AIDS", "xét nghiệm HIV", "STI"],
    },
    {
        "name": "Xét nghiệm viêm gan B (HBsAg, Anti-HBs, HBeAg)",
        "name_en": "Hepatitis B Panel",
        "procedure_type": "lab",
        "fasting": "partial",
        "fasting_hours": 4,
        "preparation": "Nhịn ăn nhẹ 4 tiếng.",
        "duration_min": 15,
        "contraindications": "Không có.",
        "notes": "HBsAg (+) → nhiễm viêm gan B. Anti-HBs (+) → miễn dịch. Cần tiêm vắc-xin nếu chưa có miễn dịch.",
        "tags": ["viêm gan B", "HBsAg", "hepatitis B", "HBV", "gan"],
    },
    {
        "name": "Xét nghiệm vi khuẩn H. pylori",
        "name_en": "H. pylori Testing (Breath Test / Biopsy)",
        "procedure_type": "lab",
        "fasting": "required",
        "fasting_hours": 4,
        "preparation": "Nhịn ăn 4 tiếng trước test hơi thở (UBT). Ngừng kháng sinh 4 tuần và thuốc PPI 2 tuần trước khi test.",
        "duration_min": 30,
        "contraindications": "Đang dùng kháng sinh hoặc PPI (ức chế bơm proton) sẽ ảnh hưởng kết quả.",
        "notes": "H. pylori là nguyên nhân chính loét dạ dày và ung thư dạ dày. Test hơi thở (UBT) không xâm lấn.",
        "tags": ["H. pylori", "HP", "loét dạ dày", "ung thư dạ dày", "UBT"],
    },
    {
        "name": "Xét nghiệm PSA – Tầm soát ung thư tiền liệt tuyến",
        "name_en": "Prostate-Specific Antigen (PSA)",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không quan hệ tình dục 48 tiếng trước. Không thăm khám trực tràng 1 tuần trước.",
        "duration_min": 15,
        "contraindications": "Kết quả PSA bị ảnh hưởng bởi viêm tuyến tiền liệt, quan hệ tình dục, xe đạp.",
        "notes": "Nam > 50 tuổi nên tầm soát PSA định kỳ. PSA > 4 ng/mL cần đánh giá thêm.",
        "tags": ["PSA", "tiền liệt tuyến", "prostate", "ung thư tiền liệt tuyến"],
    },
    {
        "name": "Đo điện não đồ (EEG)",
        "name_en": "Electroencephalogram (EEG)",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Gội đầu sạch, không dùng dầu/gel tóc. Không uống cà phê hoặc chất kích thích 24 tiếng trước. Ngủ đủ giấc tối hôm trước.",
        "duration_min": 60,
        "contraindications": "Không có tuyệt đối. Thông báo nếu đang dùng thuốc chống động kinh.",
        "notes": "Phát hiện động kinh, rối loạn điện não. Cần nằm yên trong suốt quá trình đo.",
        "tags": ["EEG", "điện não", "động kinh", "thần kinh", "co giật"],
    },
    {
        "name": "Đo chức năng hô hấp (Spirometry)",
        "name_en": "Pulmonary Function Test (Spirometry)",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không hút thuốc 4 tiếng trước. Không dùng thuốc giãn phế quản theo hướng dẫn bác sĩ. Mặc quần áo rộng.",
        "duration_min": 30,
        "contraindications": "Nhồi máu cơ tim gần đây, phẫu thuật mắt gần đây, ho ra máu.",
        "notes": "Đo FEV1, FVC để chẩn đoán hen suyễn, COPD. Sẽ yêu cầu thở mạnh nhiều lần.",
        "tags": ["spirometry", "chức năng hô hấp", "FEV1", "FVC", "COPD", "hen suyễn"],
    },
    {
        "name": "Xét nghiệm Prothrombin time / INR (đông máu)",
        "name_en": "Coagulation Test (PT/INR)",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không cần nhịn ăn. Thông báo tất cả thuốc đang dùng (đặc biệt warfarin, heparin, aspirin).",
        "duration_min": 15,
        "contraindications": "Không có.",
        "notes": "Theo dõi điều trị warfarin. INR mục tiêu phụ thuộc chỉ định (thường 2.0-3.0).",
        "tags": ["INR", "đông máu", "warfarin", "PT", "chống đông"],
    },
    {
        "name": "Sinh thiết (Biopsy)",
        "name_en": "Biopsy",
        "procedure_type": "procedure",
        "fasting": "required",
        "fasting_hours": 6,
        "preparation": "Nhịn ăn 6 tiếng (nếu dùng gây tê/gây mê). Ngừng thuốc chống đông theo chỉ định bác sĩ. Ký giấy đồng ý thủ thuật.",
        "duration_min": 30,
        "contraindications": "Rối loạn đông máu nặng, dị ứng thuốc gây tê.",
        "notes": "Loại sinh thiết phụ thuộc vị trí: kim nhỏ (FNA), kim lõi (core), phẫu thuật mở. Kết quả mô bệnh học mất 3-5 ngày.",
        "tags": ["sinh thiết", "biopsy", "ung bướu", "chẩn đoán mô bệnh học", "FNA"],
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
#  DOCUMENTS  (FAQ và hướng dẫn chung Vinmec)
# ═══════════════════════════════════════════════════════════════════════════════
DOCUMENTS = [
    {
        "title": "Giấy tờ cần mang khi đến Vinmec",
        "content": (
            "Bệnh nhân đến khám tại Vinmec cần mang theo các giấy tờ sau:\n"
            "1. CMND, CCCD hoặc hộ chiếu còn hạn (bắt buộc để đăng ký khám).\n"
            "2. Thẻ BHYT (bảo hiểm y tế) nếu có, để được hưởng quyền lợi BHYT. "
            "Lưu ý: Vinmec có một số gói dịch vụ không áp dụng BHYT.\n"
            "3. Kết quả xét nghiệm, phim chụp, hồ sơ bệnh án cũ liên quan đến lý do khám. "
            "Điều này giúp bác sĩ không phải chỉ định lại các xét nghiệm đã có.\n"
            "4. Danh sách thuốc đang dùng (toa thuốc hoặc tên thuốc + liều lượng).\n"
            "5. Thẻ thành viên Vinmec nếu có (để tích điểm và hưởng ưu đãi).\n"
            "Trẻ em dưới 15 tuổi cần thêm giấy khai sinh hoặc hộ khẩu.\n"
            "Bệnh nhân nước ngoài cần hộ chiếu (passport)."
        ),
        "category": "Hướng dẫn chung",
        "source": "Vinmec Patient Guide",
        "tags": ["giấy tờ", "CMND", "BHYT", "đăng ký khám", "documents", "hồ sơ"],
    },
    {
        "title": "Quy định nhịn ăn trước khi khám và xét nghiệm",
        "content": (
            "Nhịn ăn là yêu cầu quan trọng cho nhiều loại xét nghiệm và thủ thuật:\n"
            "- Xét nghiệm đường huyết lúc đói (FPG): nhịn ăn 8-10 tiếng.\n"
            "- Xét nghiệm mỡ máu (lipid profile): nhịn ăn 10-12 tiếng.\n"
            "- Siêu âm ổ bụng: nhịn ăn 6-8 tiếng.\n"
            "- Nội soi dạ dày: nhịn ăn 8 tiếng, nhịn nước 4 tiếng.\n"
            "- Nội soi đại tràng: nhịn ăn 24 tiếng + uống thuốc xổ theo hướng dẫn.\n"
            "- Khám sức khoẻ tổng quát: nhịn ăn 10-12 tiếng qua đêm.\n"
            "Quy tắc chung: uống nước lọc không ảnh hưởng đến đa số xét nghiệm. "
            "KHÔNG nhịn ăn khi: khám nội khoa thông thường, khám da liễu, tai mũi họng, mắt, CBC."
        ),
        "category": "Hướng dẫn nhịn ăn",
        "source": "Vinmec Clinical Guidelines",
        "tags": ["nhịn ăn", "fasting", "xét nghiệm", "nội soi", "siêu âm", "đường huyết"],
    },
    {
        "title": "Hướng dẫn đặt lịch khám tại Vinmec",
        "content": (
            "Bệnh nhân có thể đặt lịch khám tại Vinmec qua các kênh:\n"
            "1. App MyVinmec: đặt lịch, xem kết quả xét nghiệm, thanh toán trực tuyến.\n"
            "2. Website vinmec.com → Đặt lịch khám.\n"
            "3. Tổng đài: 1900 54 61 54 (7:00-20:00 các ngày trong tuần).\n"
            "4. Đến trực tiếp quầy đăng ký tại bệnh viện.\n"
            "Lưu ý quan trọng:\n"
            "- Đặt lịch trước giúp giảm thời gian chờ xuống còn 15-30 phút.\n"
            "- Đến thẳng không đặt lịch có thể chờ 1-2 tiếng.\n"
            "- Một số chuyên khoa đặc biệt (ung bướu, phẫu thuật) bắt buộc phải đặt lịch trước.\n"
            "- Nên đến trước giờ hẹn 15 phút để làm thủ tục."
        ),
        "category": "Đặt lịch",
        "source": "Vinmec Booking Guide",
        "tags": ["đặt lịch", "booking", "app MyVinmec", "tổng đài", "hẹn khám"],
    },
    {
        "title": "Thời gian dự kiến cho các loại khám tại Vinmec",
        "content": (
            "Thời gian từ khi đăng ký đến khi hoàn thành khám (đã đặt lịch trước):\n"
            "- Khám chuyên khoa thông thường (nội, tim, nhi, da liễu...): 45-90 phút.\n"
            "- Khám sức khoẻ tổng quát: 3-4 tiếng (bao gồm xét nghiệm, siêu âm, điện tim).\n"
            "- Xét nghiệm máu đơn lẻ: 20-30 phút lấy mẫu, kết quả sau 2-4 tiếng.\n"
            "- Siêu âm ổ bụng: 20-30 phút.\n"
            "- CT scan: 20-30 phút (không kể thời gian chờ đọc kết quả).\n"
            "- MRI: 45-60 phút.\n"
            "- Nội soi dạ dày: 30-45 phút (cộng thêm 30-60 phút phục hồi nếu dùng an thần).\n"
            "Kết quả xét nghiệm có trên app MyVinmec sau 2-4 tiếng làm việc."
        ),
        "category": "Thời gian",
        "source": "Vinmec Service Guide",
        "tags": ["thời gian khám", "chờ đợi", "kết quả xét nghiệm", "duration"],
    },
    {
        "title": "Lưu ý cho bệnh nhân lần đầu đến Vinmec",
        "content": (
            "Nếu đây là lần đầu đến Vinmec:\n"
            "1. Đăng ký tài khoản MyVinmec trước để đặt lịch và nhận kết quả xét nghiệm online.\n"
            "2. Đến sớm hơn giờ hẹn 15-20 phút để hoàn thành thủ tục đăng ký.\n"
            "3. Vinmec có hệ thống phân loại tầng (triage): đăng ký → đo sinh hiệu → chờ gặp bác sĩ.\n"
            "4. Đỗ xe: có bãi đỗ xe tại tầng hầm, tính phí theo giờ.\n"
            "5. Thanh toán: hỗ trợ tiền mặt, thẻ ngân hàng, ví điện tử, BHYT.\n"
            "6. Phiên dịch: có dịch vụ phiên dịch cho bệnh nhân nước ngoài (đặt trước).\n"
            "Hotline hỗ trợ: 1900 54 61 54."
        ),
        "category": "Hướng dẫn bệnh nhân mới",
        "source": "Vinmec New Patient Guide",
        "tags": ["lần đầu", "bệnh nhân mới", "first time", "đăng ký", "MyVinmec", "thủ tục"],
    },
    {
        "title": "Lưu ý đặc biệt cho phụ nữ mang thai khi đến Vinmec",
        "content": (
            "Thai phụ khi đến Vinmec cần lưu ý:\n"
            "- Luôn mang sổ khám thai/hồ sơ thai sản.\n"
            "- Thông báo tuổi thai (số tuần) cho y tá khi đăng ký.\n"
            "- Tránh X-quang trừ khi thực sự cần thiết và bác sĩ chỉ định.\n"
            "- MRI an toàn trong thai kỳ (không dùng thuốc cản quang Gadolinium nếu không cần).\n"
            "- Siêu âm thai định kỳ: tuần 6-8, 11-13, 16-20, 30-32, 36+.\n"
            "- Double Test: tuần 11-13. Triple Test: tuần 15-20.\n"
            "- Xét nghiệm tiểu đường thai kỳ (GCT/OGTT): tuần 24-28.\n"
            "- Nếu đau bụng, chảy máu âm đạo → đến khoa cấp cứu ngay, không chờ lịch hẹn."
        ),
        "category": "Thai sản",
        "source": "Vinmec Obstetrics Guide",
        "tags": ["thai sản", "mang thai", "thai phụ", "sổ khám thai", "siêu âm thai"],
    },
    {
        "title": "Hướng dẫn cho bệnh nhân đến khám tại khoa Tim mạch",
        "content": (
            "Trước khi đến khám tim mạch:\n"
            "1. Mang theo: ECG cũ, kết quả siêu âm tim, Holter ECG nếu đã làm.\n"
            "2. Liệt kê đầy đủ thuốc đang dùng (tên thuốc, liều, tần suất).\n"
            "3. KHÔNG tự ý dừng thuốc tim trước khi khám.\n"
            "4. Nhịn ăn 4 tiếng nếu bác sĩ yêu cầu xét nghiệm máu.\n"
            "5. Mặc áo rộng dễ cởi để đo ECG và siêu âm tim.\n"
            "6. Ghi lại: tần suất hồi hộp, khó thở, đau ngực, ngất xỉu.\n"
            "Nếu đang có triệu chứng đau ngực cấp, khó thở đột ngột → gọi 115 hoặc đến cấp cứu ngay."
        ),
        "category": "Tim mạch",
        "source": "Vinmec Cardiology Guide",
        "tags": ["tim mạch", "ECG", "siêu âm tim", "thuốc tim", "huyết áp", "đau ngực"],
    },
    {
        "title": "Quy định về trẻ em khi đến khám tại Vinmec",
        "content": (
            "Khi đưa trẻ đến khám tại Vinmec:\n"
            "1. Giấy tờ bắt buộc: CMND/CCCD của cha hoặc mẹ, giấy khai sinh hoặc hộ khẩu của trẻ.\n"
            "2. Thẻ BHYT trẻ em nếu có (trẻ dưới 6 tuổi được miễn phí BHYT).\n"
            "3. Sổ tiêm chủng để bác sĩ kiểm tra lịch tiêm.\n"
            "4. Thông báo tiền sử dị ứng thuốc, thức ăn của trẻ.\n"
            "5. Mang đồ chơi, sách, snack để trẻ không quấy trong thời gian chờ.\n"
            "6. Không cho trẻ ăn no trước khi lấy máu (có thể gây nôn).\n"
            "7. Phòng khám nhi riêng biệt với khu vực người lớn để tránh lây nhiễm."
        ),
        "category": "Nhi khoa",
        "source": "Vinmec Pediatrics Guide",
        "tags": ["trẻ em", "nhi khoa", "BHYT trẻ em", "tiêm chủng", "giấy khai sinh"],
    },
]
