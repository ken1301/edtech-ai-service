# Hệ thống học tập AI — Tổng quan kỹ thuật

---

## 1. Triết lí sư phạm

### 1.1 Cấu trúc chương trình học

Chương trình được tổ chức theo 3 cấp:

```
Subject → Topic → Concept
```

Mỗi **Concept** bao gồm các loại nội dung: `definition`, `formula`, `method`, `property`, `application`, `common_mistake`, `visualization`.

*Ví dụ:* `math → calculus → limits` sẽ có định nghĩa giới hạn, công thức tính giới hạn, ứng dụng thực tế, v.v.

---

### 1.2 Mô hình học tập: P-D-E-O

Học sinh vận động theo vòng lặp:

```
Problem → Done → Execute → Optimize → (Problem mới)
```

Nguyên tắc cốt lõi: **"Done > Perfect"** — hoàn thành quan trọng hơn hoàn hảo.  
Điều này được hiện thực hóa ở tầng kỹ thuật: bài làm sai vẫn tăng progress bar một phần.

---

### 1.3 Cấu trúc buổi học

Mỗi Concept có **2 buổi học**:

| | Buổi 1 | Buổi 2 |
|---|---|---|
| **Mục tiêu** | Hiểu đủ để giải bài trắc nghiệm cơ bản | Làm chủ kiến thức qua hội thoại và bài tập |
| **Hình thức** | Tự học nội dung | Chat với AI chatbot, giải 4 bài |
| **Đầu ra** | Nắm nền tảng | Progress bar đạt 100% |

---

### 1.4 Cấu trúc 4 bài tập — Buổi 2

| # | Vai trò | Mô tả |
|---|---|---|
| P1 | REINFORCEMENT | Ôn lại kiến thức buổi 1 |
| P2 | CHALLENGE | Nâng cao hơn, cùng dạng bài |
| P3 | EXPLORATION | Khó và phi quy chuẩn — phá vỡ pattern cũ |
| P4 | EXTENSION | Cùng độ khó P3, giúp học sinh tự tin với pattern mới |

Học sinh giải theo thứ tự cố định P1 → P4. Đây là quyết định có chủ đích: chuỗi P3 → P4 chỉ có tác dụng sư phạm khi đi liên tiếp.

---

### 1.5 Hành vi chatbot — Mô hình "Bạn cùng học"

Chatbot không đóng vai giáo viên mà đóng vai **bạn học cùng**:

- Chatbot **follow theo hướng tiếp cận của học sinh**, không dẫn trước
- **Kết quả đúng** → xác nhận → gợi ý học sinh tự nhận ra điểm yếu (nếu có)
- **Kết quả sai** → chatbot "nhìn từ góc của mình" để đặt câu hỏi → học sinh tự nhận ra sai lầm → lặp lại (tối đa 3 lần)
- Sau 3 lần sai cùng một lỗi → chuyển sang `SOFT_INTERVENTION`: chatbot tạm rời vai bạn học, gợi ý trực tiếp bước tiếp theo (không cho đáp án), và đề xuất bỏ qua với điểm giảm

Kỹ thuật then chốt: chatbot **"voice doubt, not diagnosis"** — *"Hmm, mình thử cách đó rồi và bị kẹt ở chỗ..."* thay vì *"Bạn quên xử lý trường hợp X."*

---

### 1.6 Cơ chế progress bar

- Có đáp án được **submit** mới tăng progress (chatbot nói đúng/sai không tính)
- Đáp án đúng → tăng nhiều; đáp án sai → tăng ít hơn (cả hai đều > 0)
- Mục tiêu: đạt 100% khi kết thúc buổi 2
- Bảo vệ khỏi *farming*: nếu phát hiện submit bừa, progress tạm dừng tăng

---

## 2. Core Engine — Kiến trúc kỹ thuật

### 2.1 Tổng quan hệ thống

```
Frontend
   │
   ▼
NestJS Service          ← auth, session persistence, rate limiting, submission validation
   │  ChatRequest (streaming)
   ▼
AI Service (Python / FastAPI)   ← stateless, xử lý toàn bộ pipeline AI
```

AI Service là **stateless**: mỗi request nhận vào toàn bộ `SessionMetadata`, xử lý, và trả về bản cập nhật. NestJS chịu trách nhiệm lưu trữ.

---

### 2.2 Pipeline 5 tầng

Request đến AI Service có thể thuộc một trong hai loại: **chat message** hoặc **submission event** (từ NestJS). Hai loại đi qua pipeline khác nhau:

```
INPUT (tin nhắn hoặc sự kiện submit)
   │
   ├── submission? ──────────────────────────────────────────────┐
   │                                                             │
   ▼                                                             ▼
[CLASSIFY]   ← fast model                                  [GROUND]   ← fast/small judge
   - Intent, cảm xúc, mức độ liên quan học tập               - Kiểm tra 2 chiều:
   - Flag: abuse / off-topic / learning-relevant                result (từ NestJS) × approach (LLM judge)
   │                                                           - Verdict: CORRECT / WEAK / INCORRECT
   ├── safety_divert  → [RESPOND: safety template]             │
   ├── fast_path_reply → [RESPOND: non-learning]               │
   │     (bỏ qua Evaluate)                                     │
   └── full_pipeline ──────────────────────────────────────────┘
                                                               │
                                                               ▼
                                                          ─────────────
                                                               │
   ┌───────────────────────────────────────────────────────────┘
   │
   ▼
[EVALUATE]   ← strong model
   - Perception only (không ra quyết định)
   - Output: phase học sinh, affect, approach hiện tại, misconception, tín hiệu kẹt
   │
   ▼
[DECIDE]   ← hybrid: deterministic rules + Tone Arbiter LLM nhỏ
   - Input: EvaluateOutput + GroundOutput + SessionState
   - Output: response_class, tone, depth, advance?, intervene?
   │
   ▼
[RESPOND]   ← mid-tier model, prompt theo phase × response_class
   - Sinh văn bản streaming gửi về NestJS
   │
   ▼
[STATE WRITER]   ← deterministic, không dùng LLM
   - Cập nhật: attempts, misconceptions, compression, progress_delta
   - Trả về SessionMetadata đã cập nhật
```

---

### 2.3 Ma trận hành vi submission (2 chiều)

Ground kiểm tra độc lập hai chiều:

| | `approach` đúng | `approach` sai / yếu |
|---|---|---|
| `result` đúng (từ NestJS) | Xác nhận, advance ngay | Xác nhận kết quả, gợi ý điểm yếu của cách làm |
| `result` sai (từ NestJS) | Giữ nguyên, chatbot "đặt câu hỏi nhẹ" | COUNTER_PERSPECTIVE — chatbot phản ánh góc nhìn |

Tách 2 chiều này là quyết định kiến trúc quan trọng nhất: tránh trường hợp học sinh làm đúng bằng cách làm sai mà chatbot vẫn xác nhận hoàn toàn.

### 2.4 Nguyên tắc thiết kế cứng

1. **LLM chỉ trả JSON có schema** — không có LLM nào ghi trực tiếp vào state
2. **Chỉ Orchestrator mới mutate SessionMetadata** — LLM layers chỉ đọc và trả output
3. **Ground là layer duy nhất thấy `final_answer` thô** — các layer sau chỉ thấy verdict
4. **Branching xảy ra trong orchestrator code**, không trong prompt

---

### 2.5 Công nghệ

| Layer | Tech |
|---|---|
| AI Service | Python, FastAPI, kiến trúc hexagonal |
| Communication | Streaming (SSE) từ AI Service → NestJS |
| Backend Service | NestJS (auth, session, submission) |
| LLM tiers | Strong model (Evaluate), mid-tier/fast (Respond, Decide Tone Arbiter), fast/small (Classify, Ground judge) |

---