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

## Technical teacher pipeline (Create lesson)
` Subject, Topic, Concept are python Enum `
1. Create general info (title, subject, topic, concept)
2. Part 1 setup (Update soon)
3. Part 2 setup
- Input: document (pdf, docx, txt, markdown) or rich text input
- Process:
    - NestJS backend receives input, saves to S3, and sends document URL to AI service "/exercise/extract/lesson2", this endpoint request:
    ```json
    {
    "user_id": "string",
    "correlation_id": "string",
    "document_url": "string",
    "subject": "string",
    "topic": "string",
    "concept": "string"
    }
    ```
    - AI service receives document URL, downloads document, processes it (parsing, cleaning, LLM extraction), and generates structured exercises. Its response: 
    ```json
    {
    "output": {
        "problem_list": [
        {
            "problem_id": 0,
            "question": "string",
            "attachment_url": ["string"],
            "approach_list": [
            {
                "summary": "string",
                "bloom_level": "remember",  // enum
                "concept_type_used": [
                "definition"    // list of enum
                ],
                "pattern": {
                "cognitive_operation": [
                    "recall"    // list of enum
                ],
                "representation": [
                    "symbolic"  // list of enum
                ],
                "constraints": [
                    "domain"    // list of enum
                ]
                },
                "approach_answer": "string",
                "strengths": [
                "optimal_complexity"    // list of enum
                ],
                "weaknesses": [
                "high_time_complexity"  // list of enum
                ],
                "max_attempts": 0
            }
            ],
            "final_answer": "string",
            "open_approach": true,
            "recommended_problem_role": "reinforcement",    // enum
            "max_approach_trial": 0
        }
        ],
        "subject": "math",
        "topic": "algebra",
        "concept": "linear_equations",
        "user_id": "string"
    },
    "usage": {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "estimated_cost": 0
    },
    "correlation_id": "string"
    }
    ```
    - NestJS receives response, takes the "response.output" and displays it in the frontend for teacher review. Teacher can edit exercises if needed, then confirms.
4. Final confirmation: after confirming 2 parts, teacher fills in final form (class assignment, publish settings), then submits. NestJS stores lesson data (part 1 and part 2) in MongoDB, and makes it available for students.


## Technical student pipeline (Study with AI chatbot)
` Subject, Topic, Concept are python Enum `
1. In the learning path, student clicks on a lesson
2. Student sees lesson view with 2 parts:
- Part 1: study material on the left, exercise on the right. Exercise is interactive, student can input answer and get feedback.
- Part 2: 
    - Opening of this part: NestJS sends request to AI service "/exercise/select/lesson2" with:
    ```json
    {
    "exercise_id": "string",
    "user_id": "string",
    "correlation_id": "string"
    }
    ```
    - AI service receives request, retrieves exercise data, and selects appropriate problems for the student based on their profile and history. It responds with:
    ```json
    {   
        // selected_problems in a list of 4 problems
        "selected_problems": [
        {
            "problem_id": 0,
            "question": "string",
            "attachment_url": ["string"],
            "approach_list": [
            {
                "summary": "string",
                "bloom_level": "remember",  // enum
                "concept_type_used": [
                "definition"    // list of enum
                ],
                "pattern": {
                "cognitive_operation": [
                    "recall"    // list of enum
                ],
                "representation": [
                    "symbolic"  // list of enum
                ],
                "constraints": [
                    "domain"    // list of enum
                ]
                },
                "approach_answer": "string",
                "strengths": [
                "optimal_complexity"    // list of enum
                ],
                "weaknesses": [
                "high_time_complexity"  // list of enum
                ],
                "max_attempts": 0
            }
            ],
            "final_answer": "string",
            "open_approach": true,
            "recommended_problem_role": "reinforcement",    // enum
            "max_approach_trial": 0
        }
        ],
        "correlation_id": "string"
    }
    ```
    - NestJS receives response, then create a redis key: "session:{session_id}:metadata" with value: 
    ```json
    {
    "session_id": null, 
    "user_id": null,
    "subject": null,
    "topic": null,
    "concept": null,
    "history_phase": [],
    "phase_cycle_count": 0,
    "problem_list": [],
    "current_problem_id": null,
    "problem_state": {},
    "misconception_list": [],
    "emotion_history": [],
    "last_evaluate_summary": null,
    "history_compression": null,
    "created_at": null,
    "turn_count": 0,
    "history_summary": "",
    "current_progress": 0.0,
    "is_active": true,
    "closed_at": null
    }
    ```
    - Student interacts with chatbot, NestJS sends a request to AI service "/chat" with:
    ```json
    {
    "user_id": "string",
    "session_id": "string",
    "correlation_id": "string",
    "subject": "math",
    "topic": "algebra",
    "concept": "linear_equations",
    "user_msg": "string",
    "is_submission": true,
    "submission_data": {
        "status": true,
        "is_process_farm": [
        null, // bool
        null  // int: process farm counter
        ]
    }
    }
    ```
    - AI service receives request, processes and generate response:
    ```json
    {
    "content": "string", // chatbot response content
    "usage": [
        "string"
    ],
    "correlation_id": "string",
    "current_process": 0.0 // updated progress after this interaction
    }
    ```
    - NestJS time counter (60 min/session), nestJS sends request to AI service "/chat/sync_and_close" with:
    ```json
    {
    "user_id": "string",
    "session_id": "string",
    "correlation_id": "string",
    "subject": "math",
    "topic": "algebra",
    "concept": "linear_equations"
    }
    ```




