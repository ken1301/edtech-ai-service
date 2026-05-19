Tôi muốn tạo ra 1 chatbot 
```
{
  name: str,
  grade: str,
  preference: {
    strengths: [],
    weaknesses: [],
    learning_style: str,
    preferred_difficulty: str,
  },
  knowledge_map: [
    <subject>: [
      <topic>: {
        score: float,
        misconceptions: [str],
        summary: str
      }
    ]
  ],
  
  thinking_metric: {}, # tập trung đánh giá sâu vào cách học sinh suy nghĩ, tiếp cận và nhận thức vấn đề
  skill_metric: {}, # đo lường cách thức học sinh thao tác và thực thi các bước giải quyết vấn đề thực tế
  result_metric: {}, # đánh giá kết quả cuối cùng của học sinh, bao gồm điểm số bài kiểm tra, tốc độ giải quyết vấn đề, và độ chính xác của câu trả lời
}
```

