Current frontend:
- Login Form: Centered card, minimalist.
- Student Dashboard: Radar chart, enrolled classes grid, incomplete lessons checklist.
- Lesson Dashboard (Learning Path): Duolingo-style sequential roadmap.
- Teacher Dashboard: 3-column layout (Classes, Class Details with Tabs, Student Detail/Radar Chart).
- Create Lesson Page: Step-by-step form (Document upload, Rich text, Settings, Class assignment).
- Lesson View 1 (Material + Quiz): Split-screen (Quiz vs Study Material).
- Lesson View 2 (AI-Assisted): Exercises list + Persistent AI Chatbot.
- Navigation & Layout Components: Role-based Sidebar/Navbar, Profile dropdown.

## User story (1 lesson - 2 part)
### Teacher 
- step 1: login
- step 2: view dashboard with classes and students
- step 3: click "New lesson", 4 steps:
    - 1. create general info (title, subject, topic, concept)
    - 2. part 1 setup: upload document (pdf, docx, txt, markdown), or input text directly (rich text editor), then LLM extracts key points and generates exercises (multiple choice, short answer). Teacher reviews and edits exercises if needed
    - 3. part 2 setup: upload exercise document or input exercises directly, then LLM generates structured exercises and solutions. Teacher reviews and edits if needed
    - 4. assign lesson to class
### Student
- step 1: login
- step 2: view dashboard with enrolled classes and lessons, see progress and incomplete lessons
- step 3: click on class, view learning path with sequential lessons, click on lesson:
    - part 1: view study material on left, exercises on right. Exercises are interactive, student can input answer and get feedback. 
    - part 2: AI chatbot in the middle, student can ask questions about the material or exercises, chatbot can provide hints, explanations. Student study with chatbot with the problem list on the side.
- step 4: after completing the lesson, student can see summary of what they learned, and update their profile with preferences and knowledge map.
- step 5: student can view their progress and updated profile on the dashboard.

## Technical teacher pipeline

1. Part 1 setup




