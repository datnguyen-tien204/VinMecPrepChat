"""
app/rag/medical_data_extra.py – Dữ liệu bổ sung cho Vinmec RAG.

Append vào SPECIALTIES, PROCEDURES, DOCUMENTS từ medical_data.py.
Chạy ingest_medical_data.py --reset sau khi thêm file này vào imports.

Thêm:
  SPECIALTIES_EXTRA  – 5 chuyên khoa còn thiếu
  PROCEDURES_EXTRA   – 8 xét nghiệm/thủ thuật còn thiếu
  DOCUMENTS_EXTRA    – 3 tài liệu hướng dẫn bổ sung
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  SPECIALTIES_EXTRA  (5 chuyên khoa còn thiếu)
# ═══════════════════════════════════════════════════════════════════════════════
SPECIALTIES_EXTRA = [
    {
        "name": "Răng hàm mặt",
        "name_en": "Dentistry & Oral Surgery",
        "department": "Răng Hàm Mặt",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '[\"CMND/CCCD\", \"Thẻ BHYT (nếu có)\", \"Phim X-quang răng cũ (nếu có)\", \"Hồ sơ điều trị nha khoa trước đây\"]',
        "booking_required": True,
        "estimated_duration_min": 45,
        "notes": (
            "Không ăn uống ít nhất 2 tiếng trước nếu dự kiến nhổ răng hoặc tiểu phẫu. "
            "Thông báo nếu đang dùng thuốc chống đông (aspirin, warfarin) — cần ngừng trước 3-5 ngày theo hướng dẫn bác sĩ. "
            "Thông báo tiền sử dị ứng thuốc tê (lidocaine). Súc miệng sạch trước khi đến."
        ),
        "tags": ["răng hàm mặt", "nha khoa", "dentistry", "nhổ răng", "niềng răng", "răng khôn", "implant", "trám răng"],
    },
    {
        "name": "Dị ứng – Miễn dịch lâm sàng",
        "name_en": "Allergy & Clinical Immunology",
        "department": "Dị Ứng – Miễn Dịch",
        "fasting": "none",
        "fasting_hours": 0,
        "documents": '[\"CMND/CCCD\", \"Thẻ BHYT (nếu có)\", \"Danh sách thuốc đang dùng (đặc biệt antihistamine)\", \"Hồ sơ dị ứng cũ nếu có\"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": (
            "QUAN TRỌNG: Ngừng thuốc kháng histamine (cetirizine, loratadine, diphenhydramine...) "
            "ít nhất 5-7 ngày trước khi làm test dị ứng — thuốc này ức chế phản ứng làm sai kết quả. "
            "Không dùng corticosteroid đường toàn thân 2 tuần trước. "
            "Mặc áo tay ngắn để bác sĩ dễ làm test lẩy da ở cẳng tay. "
            "Thông báo nếu đã từng có phản ứng phản vệ (anaphylaxis)."
        ),
        "tags": ["dị ứng", "miễn dịch", "allergy", "immunology", "nổi mề đay", "hen dị ứng", "dị ứng thức ăn", "dị ứng thuốc"],
    },
    {
        "name": "Lão khoa",
        "name_en": "Geriatrics",
        "department": "Lão Khoa",
        "fasting": "partial",
        "fasting_hours": 4,
        "documents": '[\"CMND/CCCD\", \"Thẻ BHYT (nếu có)\", \"Danh sách đầy đủ tất cả thuốc đang dùng (tên + liều)\", \"Kết quả xét nghiệm 3 tháng gần nhất\", \"Sổ theo dõi bệnh mạn tính (huyết áp, đường huyết)\"]',
        "booking_required": True,
        "estimated_duration_min": 90,
        "notes": (
            "Người thân nên đi cùng để hỗ trợ cung cấp thông tin bệnh sử. "
            "Mang theo TẤT CẢ thuốc đang uống kể cả thực phẩm chức năng — polypharmacy là vấn đề phổ biến ở người cao tuổi. "
            "Đánh giá toàn diện: nhận thức (MMSE), té ngã, dinh dưỡng, khả năng vận động. "
            "Nhịn ăn 4 tiếng nếu cần xét nghiệm máu thường quy."
        ),
        "tags": ["lão khoa", "người cao tuổi", "geriatrics", "sa sút trí tuệ", "Alzheimer", "té ngã", "đa bệnh"],
    },
    {
        "name": "Huyết học lâm sàng",
        "name_en": "Hematology",
        "department": "Huyết Học",
        "fasting": "partial",
        "fasting_hours": 4,
        "documents": '[\"CMND/CCCD\", \"Thẻ BHYT (nếu có)\", \"Kết quả CBC, tủy đồ cũ (nếu có)\", \"Hồ sơ điều trị hóa chất (nếu đang điều trị)\"]',
        "booking_required": True,
        "estimated_duration_min": 90,
        "notes": (
            "Nhịn ăn 4 tiếng cho xét nghiệm máu. "
            "Thủ thuật chọc tủy xương (bone marrow biopsy) cần nhịn ăn 6 tiếng và có chỉ định riêng. "
            "Thông báo nếu đang dùng thuốc ảnh hưởng đến tủy xương. "
            "Kết quả xét nghiệm đặc thù (điện di hemoglobin, đông máu nâng cao) có thể trả sau 3-5 ngày."
        ),
        "tags": ["huyết học", "hematology", "thiếu máu", "bạch cầu", "thalassemia", "lymphoma", "leukemia", "đông máu"],
    },
    {
        "name": "Dinh dưỡng lâm sàng",
        "name_en": "Clinical Nutrition",
        "department": "Dinh Dưỡng",
        "fasting": "required",
        "fasting_hours": 8,
        "documents": '[\"CMND/CCCD\", \"Thẻ BHYT (nếu có)\", \"Kết quả xét nghiệm lipid, glucose, albumin (nếu có)\", \"Nhật ký thực phẩm 3 ngày (nếu được yêu cầu)\"]',
        "booking_required": True,
        "estimated_duration_min": 60,
        "notes": (
            "Nhịn ăn 8 tiếng để đo thành phần cơ thể (InBody) và xét nghiệm dinh dưỡng chính xác. "
            "Uống đủ nước trước khi đo InBody (không mất nước). "
            "Ghi lại thực phẩm ăn trong 3 ngày trước nếu tư vấn dinh dưỡng điều trị. "
            "Mặc quần áo mỏng nhẹ để cân và đo chính xác."
        ),
        "tags": ["dinh dưỡng", "nutrition", "InBody", "béo phì", "suy dinh dưỡng", "ăn kiêng", "chế độ ăn"],
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
#  PROCEDURES_EXTRA  (8 xét nghiệm / thủ thuật còn thiếu)
# ═══════════════════════════════════════════════════════════════════════════════
PROCEDURES_EXTRA = [
    {
        "name": "Chụp nhũ ảnh (Mammography)",
        "name_en": "Mammography",
        "procedure_type": "imaging",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": (
            "Không bôi kem dưỡng da, phấn rôm, hoặc chất khử mùi vùng ngực và nách trước khi chụp. "
            "Mặc áo dễ cởi. Tốt nhất nên chụp trong tuần 1-2 của chu kỳ kinh nguyệt "
            "(ngực ít đau và mô mềm hơn). "
            "Mang phim nhũ ảnh cũ nếu có để so sánh."
        ),
        "duration_min": 20,
        "contraindications": "Phụ nữ mang thai (trừ trường hợp cấp thiết). Không áp dụng cho người đặt implant ngực — cần kỹ thuật đặc biệt.",
        "notes": (
            "Tầm soát ung thư vú. Phụ nữ ≥ 40 tuổi nên chụp định kỳ 1-2 năm/lần. "
            "Có thể hơi đau do kẹp chặt ngực — là cần thiết để có ảnh rõ. "
            "Kết quả BI-RADS 0-6; BI-RADS ≥ 4 cần sinh thiết."
        ),
        "tags": ["nhũ ảnh", "mammography", "ung thư vú", "tầm soát vú", "BI-RADS", "phụ khoa"],
    },
    {
        "name": "Nghiệm pháp dung nạp glucose (OGTT)",
        "name_en": "Oral Glucose Tolerance Test (OGTT)",
        "procedure_type": "lab",
        "fasting": "required",
        "fasting_hours": 8,
        "preparation": (
            "Nhịn ăn ít nhất 8-10 tiếng (có thể uống nước lọc). "
            "3 ngày trước: ăn bình thường (không ăn kiêng carbohydrate — ảnh hưởng kết quả). "
            "Ngày làm test: đến đúng giờ, ngồi nghỉ 15 phút trước khi lấy máu lần 1. "
            "Uống 75g glucose (hoặc 50g với GCT sàng lọc thai kỳ) trong 5 phút. "
            "Ở lại bệnh viện 2 tiếng, lấy máu lại sau 1 giờ và 2 giờ."
        ),
        "duration_min": 135,
        "contraindications": "Đường huyết lúc đói > 11.1 mmol/L (không làm OGTT, đã xác định tiểu đường).",
        "notes": (
            "Chẩn đoán tiểu đường thai kỳ (tuần 24-28) và tiểu đường típ 2. "
            "Không rời bệnh viện giữa chừng. Không ăn uống hoặc vận động mạnh trong thời gian chờ. "
            "OGTT 2h ≥ 11.1 mmol/L → tiểu đường. 7.8-11.0 mmol/L → rối loạn dung nạp glucose."
        ),
        "tags": ["OGTT", "GCT", "tiểu đường thai kỳ", "glucose", "dung nạp glucose", "tiểu đường"],
    },
    {
        "name": "Điện cơ đồ và đo dẫn truyền thần kinh (EMG/NCS)",
        "name_en": "Electromyography & Nerve Conduction Study (EMG/NCS)",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": (
            "Không bôi kem dưỡng da tay/chân trước khi đến. "
            "Tắm sạch vùng được khảo sát. "
            "Thông báo nếu đang dùng thuốc chống đông máu (kim điện cực nhỏ được đưa vào cơ). "
            "Mặc quần áo rộng, dễ cởi."
        ),
        "duration_min": 60,
        "contraindications": "Máy tạo nhịp tim (relative), rối loạn đông máu nặng (đối với kim EMG).",
        "notes": (
            "Đánh giá bệnh thần kinh ngoại biên, hội chứng ống cổ tay, ALS, bệnh cơ. "
            "NCS (đo dẫn truyền) không đau. Kim EMG có thể hơi khó chịu. "
            "Thời gian từ 45-90 phút tùy số vị trí khảo sát. "
            "Không ảnh hưởng bởi thuốc thần kinh ngoại biên thông thường."
        ),
        "tags": ["EMG", "NCS", "điện cơ", "dẫn truyền thần kinh", "hội chứng ống cổ tay", "thần kinh ngoại biên"],
    },
    {
        "name": "Xét nghiệm Vitamin D (25-OH Vitamin D)",
        "name_en": "25-OH Vitamin D Test",
        "procedure_type": "lab",
        "fasting": "partial",
        "fasting_hours": 4,
        "preparation": (
            "Nhịn ăn nhẹ 4 tiếng. "
            "Thông báo nếu đang bổ sung Vitamin D liều cao — có thể ngừng 3-5 ngày trước nếu bác sĩ yêu cầu. "
            "Có thể kết hợp với xét nghiệm canxi, PTH trong cùng mẫu máu."
        ),
        "duration_min": 15,
        "contraindications": "Không có.",
        "notes": (
            "< 20 ng/mL: thiếu hụt Vitamin D. 20-30 ng/mL: không đủ. > 30 ng/mL: đủ. "
            "Kết quả trả trong ngày. Thường kết hợp với xét nghiệm loãng xương, "
            "suy giáp, hoặc bệnh nhân lớn tuổi ít ra ngoài."
        ),
        "tags": ["vitamin D", "25-OH", "thiếu vitamin D", "loãng xương", "canxi", "xét nghiệm máu"],
    },
    {
        "name": "Test lẩy da dị ứng (Skin Prick Test)",
        "name_en": "Allergy Skin Prick Test (SPT)",
        "procedure_type": "procedure",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": (
            "QUAN TRỌNG: Ngừng kháng histamine (cetirizine, loratadine, fexofenadine, diphenhydramine) "
            "ít nhất 5-7 ngày trước. Ngừng corticosteroid đường toàn thân 2 tuần trước. "
            "Không ngừng thuốc hen (ventolin, seretide) — tiếp tục dùng bình thường. "
            "Mặc áo tay ngắn. Không bôi kem dưỡng da cẳng tay."
        ),
        "duration_min": 40,
        "contraindications": (
            "Tiền sử phản vệ nặng với dị nguyên được test (làm tại phòng cấp cứu có epinephrine). "
            "Đang đợt cấp hen nặng. Đang dùng beta-blocker (giảm khả năng cấp cứu nếu có phản ứng)."
        ),
        "notes": (
            "Đọc kết quả sau 15-20 phút: sẩn ≥ 3mm là dương tính. "
            "Thử được nhiều dị nguyên cùng lúc: bụi nhà, mạt bụi, phấn hoa, thức ăn, lông thú. "
            "Ngay sau test cần ở lại 30 phút để theo dõi phản ứng toàn thân."
        ),
        "tags": ["test dị ứng", "skin prick test", "SPT", "dị ứng", "mạt bụi", "phấn hoa", "dị nguyên"],
    },
    {
        "name": "Xét nghiệm D-dimer",
        "name_en": "D-dimer Test",
        "procedure_type": "lab",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": "Không cần chuẩn bị đặc biệt. Thông báo nếu đang điều trị anticoagulant (warfarin, rivaroxaban, heparin).",
        "duration_min": 15,
        "contraindications": "Không có.",
        "notes": (
            "Tầm soát huyết khối tĩnh mạch sâu (DVT) và thuyên tắc phổi (PE). "
            "D-dimer tăng trong nhiều tình huống (viêm, phẫu thuật, mang thai, ung thư) → "
            "chỉ có giá trị âm tính để loại trừ DVT/PE khi lâm sàng nghi ngờ thấp. "
            "Kết quả có trong 1-2 giờ."
        ),
        "tags": ["D-dimer", "huyết khối", "DVT", "thuyên tắc phổi", "PE", "đông máu", "xét nghiệm máu"],
    },
    {
        "name": "Siêu âm tuyến giáp",
        "name_en": "Thyroid Ultrasound",
        "procedure_type": "imaging",
        "fasting": "none",
        "fasting_hours": 0,
        "preparation": (
            "Không cần chuẩn bị đặc biệt. "
            "Mặc áo cổ rộng hoặc cổ chữ V để bác sĩ dễ tiếp cận vùng cổ. "
            "Không đeo vòng cổ, khăn quàng."
        ),
        "duration_min": 20,
        "contraindications": "Không có.",
        "notes": (
            "Đánh giá kích thước, cấu trúc, nhân tuyến giáp. "
            "Phân loại nhân giáp theo TIRADS (1-5). TIRADS ≥ 4 thường cần FNA (sinh thiết kim nhỏ). "
            "Không đau, không cần gây tê. Thường kết hợp với xét nghiệm TSH/FT3/FT4."
        ),
        "tags": ["siêu âm tuyến giáp", "thyroid ultrasound", "nhân giáp", "TIRADS", "bướu giáp", "ung thư giáp"],
    },
    {
        "name": "Nghiệm pháp gắng sức tim (Exercise Stress Test – EST)",
        "name_en": "Exercise Stress Test (Treadmill ECG)",
        "procedure_type": "procedure",
        "fasting": "required",
        "fasting_hours": 3,
        "preparation": (
            "Nhịn ăn nhẹ 3 tiếng trước (không nhịn hoàn toàn). "
            "Mặc quần áo thể thao, giày thể thao có đế bằng. "
            "Không uống cà phê, thuốc lá 3 tiếng trước. "
            "Thông báo tất cả thuốc đang dùng — một số thuốc tim mạch cần điều chỉnh theo chỉ định. "
            "Tránh tập thể dục nặng ngày hôm trước."
        ),
        "duration_min": 60,
        "contraindications": (
            "Nhồi máu cơ tim cấp (< 48h), đau thắt ngực không ổn định, "
            "hẹp van động mạch chủ nặng, huyết áp > 200/110 mmHg, suy tim mất bù."
        ),
        "notes": (
            "Theo dõi ECG và huyết áp trong khi đi bộ/chạy trên máy chạy tốc độ tăng dần. "
            "Test dừng nếu đau ngực, chóng mặt, thay đổi ECG nguy hiểm, hoặc đạt nhịp tim mục tiêu. "
            "Sau test nghỉ 30 phút theo dõi tiếp. Cần người đi cùng về."
        ),
        "tags": ["stress test", "EST", "gắng sức tim", "treadmill", "ECG gắng sức", "thiếu máu cơ tim", "tim mạch"],
    },
]

# ═══════════════════════════════════════════════════════════════════════════════
#  DOCUMENTS_EXTRA  (3 tài liệu hướng dẫn bổ sung)
# ═══════════════════════════════════════════════════════════════════════════════
DOCUMENTS_EXTRA = [
    {
        "title": "Hướng dẫn về Bảo hiểm y tế (BHYT) tại Vinmec",
        "content": (
            "Vinmec là bệnh viện tư nhân có hợp đồng khám chữa bệnh BHYT với một số gói dịch vụ.\n"
            "Điều quan trọng cần biết:\n"
            "1. Vinmec thanh toán BHYT theo hướng dẫn của BHXH Việt Nam. Mức hưởng phụ thuộc "
            "vào đúng tuyến/trái tuyến và loại dịch vụ.\n"
            "2. Đúng tuyến (có giấy chuyển viện hợp lệ): BHYT chi trả 40-100% tùy mức thẻ.\n"
            "3. Trái tuyến (tự đến không có giấy chuyển): BHYT chỉ hỗ trợ một phần nhỏ (30% ở tuyến Trung ương).\n"
            "4. Một số dịch vụ cao cấp của Vinmec (phòng dịch vụ, xét nghiệm theo yêu cầu) KHÔNG được BHYT thanh toán.\n"
            "5. Trẻ em dưới 6 tuổi có thẻ BHYT được miễn viện phí (phần BHYT chi trả 100%).\n"
            "6. Người có thẻ BHYT cần mang: thẻ BHYT gốc + CMND + giấy chuyển viện (nếu có).\n"
            "Hotline hỏi về BHYT tại Vinmec: 1900 54 61 54 (chọn phím 2)."
        ),
        "category": "Tài chính – BHYT",
        "source": "Vinmec Insurance Guide",
        "tags": ["BHYT", "bảo hiểm y tế", "viện phí", "chuyển tuyến", "tự đến", "chi trả"],
    },
    {
        "title": "Hướng dẫn đặc biệt cho bệnh nhân cao tuổi (≥ 65 tuổi) khi đến Vinmec",
        "content": (
            "Vinmec có chính sách ưu tiên cho bệnh nhân cao tuổi:\n"
            "1. Ưu tiên đăng ký và khám trước (xuất trình CMND ghi rõ năm sinh hoặc thẻ người cao tuổi).\n"
            "2. Có xe lăn miễn phí tại cổng vào — yêu cầu nhân viên bảo vệ hỗ trợ.\n"
            "3. Người thân hoặc người hỗ trợ được vào cùng trong phòng khám.\n"
            "4. Khi đăng ký, thông báo với lễ tân:\n"
            "   - Danh sách đầy đủ tất cả thuốc đang uống (kể cả vitamin, thực phẩm chức năng).\n"
            "   - Tiền sử té ngã, mất thăng bằng.\n"
            "   - Tình trạng nhận thức (sa sút trí tuệ nếu có).\n"
            "5. Nên đặt lịch vào buổi sáng sớm (8-9h) để tránh xếp hàng và bệnh nhân chưa đông.\n"
            "6. Mang đủ thuốc dùng trong ngày vì có thể chờ 2-3 tiếng.\n"
            "7. Thông báo trước nếu bệnh nhân cần phiên dịch (phương ngữ địa phương, tiếng dân tộc)."
        ),
        "category": "Hướng dẫn bệnh nhân đặc biệt",
        "source": "Vinmec Elderly Patient Guide",
        "tags": ["người cao tuổi", "lão khoa", "ưu tiên", "xe lăn", "hỗ trợ", "elderly", "65 tuổi"],
    },
    {
        "title": "Hướng dẫn sau khi nhận kết quả xét nghiệm tại Vinmec",
        "content": (
            "Sau khi có kết quả xét nghiệm từ Vinmec:\n"
            "1. Kết quả xét nghiệm máu thông thường có trên app MyVinmec sau 2-4 giờ làm việc.\n"
            "2. Kết quả phức tạp (giải phẫu bệnh, vi sinh, xét nghiệm phân tử) có sau 3-7 ngày — "
            "nhân viên sẽ thông báo qua số điện thoại đã đăng ký.\n"
            "3. Chỉ bác sĩ Vinmec có thể tư vấn và giải thích kết quả. "
            "Không tự ý điều chỉnh thuốc dựa trên kết quả khi chưa gặp bác sĩ.\n"
            "4. Nếu có chỉ số bất thường cần xử trí cấp: Vinmec sẽ gọi điện trực tiếp cho bệnh nhân.\n"
            "5. Để giữ bản cứng: đến quầy trả kết quả trong 30 ngày kể từ ngày có kết quả.\n"
            "6. Đặt lịch tái khám để bác sĩ đọc kết quả:\n"
            "   - App MyVinmec → Lịch sử khám → Đặt lịch tái khám\n"
            "   - Hotline: 1900 54 61 54\n"
            "7. Kết quả hình ảnh (X-quang, CT, MRI, siêu âm): lấy CD/phim tại phòng chẩn đoán hình ảnh "
            "trong vòng 30 ngày."
        ),
        "category": "Sau khám",
        "source": "Vinmec Post-Visit Guide",
        "tags": ["kết quả xét nghiệm", "MyVinmec", "tái khám", "giải thích kết quả", "bất thường", "sau khám"],
    },
]
