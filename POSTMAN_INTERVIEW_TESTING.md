# 🧪 Postman Testing Guide - Batch Interview Processing

## 📋 Prerequisites

1. **Server Running**: Ensure Django server is running on `http://localhost:8000`
2. **Authentication**: Get a valid JWT token from login
3. **CV Uploaded**: Have a CV uploaded for the user
4. **Postman Setup**: Import the requests below

---

## 🔐 Step 1: Authentication

### Login to Get JWT Token
```
POST http://localhost:8000/api/auth/login/
Content-Type: application/json

{
  "email": "your-email@example.com",
  "password": "your-password"
}
```

**Copy the `access` token from response for use in subsequent requests.**

---

## 📄 Step 2: Upload CV (Optional)

If you don't have a CV uploaded yet:

```
POST http://localhost:8000/api/rag/cv-upload/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: multipart/form-data

# Form data:
# file: [select your CV file - .pdf, .docx, or .txt]
```

---

## 🎯 Step 3: Generate Interview Questions (NEW BATCH FLOW)

```
POST http://localhost:8000/api/interview/questions/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "job_description": "Senior Full Stack Developer position requiring 5+ years experience with React, Node.js, PostgreSQL, and AWS. Must have experience with microservices architecture, CI/CD pipelines, and team leadership. Strong problem-solving skills and ability to mentor junior developers required.",
  "question_count": 5,
  "difficulty": "medium"
}
```

**Expected Response:**
```json
{
  "session_id": "uuid-here",
  "questions": [
    {
      "id": "question-1-uuid",
      "question": "Tell me about a challenging full-stack project you led...",
      "category": "behavioral",
      "difficulty": "medium",
      "tips": "Use STAR method",
      "expected_answer_focus": "leadership and technical skills"
    }
  ],
  "job_description": "Senior Full Stack Developer...",
  "difficulty": "medium", 
  "question_count": 5,
  "instructions": "Answer all questions, then use /api/interview/submit-all-answers/ to submit all answers for batch evaluation.",
  "flow": "batch_processing"
}
```

**📝 Save the `session_id` and question `id`s for the next step!**

---

## 📝 Step 4: Submit All Answers for Batch Evaluation (NEW)

```
POST http://localhost:8000/api/interview/submit-all-answers/
Authorization: Bearer YOUR_JWT_TOKEN
Content-Type: application/json

{
  "session_id": "SESSION_ID_FROM_STEP_3",
  "answers": [
    {
      "question_id": "QUESTION_1_ID",
      "user_answer": "I led a team of 6 developers to build a microservices-based e-commerce platform. The main challenge was migrating from a monolithic architecture while maintaining zero downtime. I implemented a strangler fig pattern, gradually replacing components. We used Docker containers, Kubernetes for orchestration, and implemented CI/CD with Jenkins. The project took 8 months and resulted in 40% better performance and 60% faster deployment cycles."
    },
    {
      "question_id": "QUESTION_2_ID", 
      "user_answer": "For React state management, I choose based on complexity. For simple apps, I use useState and useContext. For medium complexity, I prefer Zustand for its simplicity. For large enterprise apps, I use Redux Toolkit with RTK Query for server state. I also implement proper memoization with useMemo and useCallback to prevent unnecessary re-renders."
    },
    {
      "question_id": "QUESTION_3_ID",
      "user_answer": "I mentor junior developers through code reviews, pair programming sessions, and weekly one-on-ones. I create learning paths based on their goals, assign progressively challenging tasks, and encourage them to present their solutions to the team. I also organize tech talks and maintain internal documentation. My approach focuses on building confidence while ensuring code quality."
    },
    {
      "question_id": "QUESTION_4_ID",
      "user_answer": "I handle production issues by first assessing severity and impact. For critical issues, I immediately notify stakeholders and implement temporary fixes if needed. I use monitoring tools like DataDog and Sentry to identify root causes. I document all incidents, conduct post-mortems, and implement preventive measures. Communication is key - I keep all stakeholders updated throughout the resolution process."
    },
    {
      "question_id": "QUESTION_5_ID",
      "user_answer": "I stay current through multiple channels: following tech blogs like Hacker News and Dev.to, attending conferences and webinars, participating in online communities, and working on side projects. I dedicate 2 hours weekly to learning new technologies. I also contribute to open source projects and maintain a learning journal to track my progress."
    }
  ]
}
```

**Expected Response:**
```json
{
  "session_id": "session-uuid",
  "total_questions": 5,
  "total_evaluations": 5,
  "average_score": 82.3,
  "evaluations": [
    {
      "evaluation_id": "eval-uuid",
      "answer_id": "answer-uuid", 
      "question_id": "question-uuid",
      "question": "Tell me about a challenging project...",
      "user_answer": "I led a team of 6 developers...",
      "evaluation": {
        "overall_score": 85,
        "strengths": ["Clear leadership example", "Quantifiable results"],
        "weaknesses": ["Could elaborate on team challenges"],
        "correct_answer": "The ideal answer would include...",
        "answer_analysis": "Strong technical leadership example...",
        "improvement_tips": ["Add team management details"],
        "follow_up_questions": ["How did you handle conflicts?"]
      }
    }
  ],
  "session_complete": true,
  "message": "All answers evaluated successfully using batch AI processing"
}
```

---

## 📊 Step 5: View Interview History

### Get Session Summary
```
GET http://localhost:8000/api/interview/history/
Authorization: Bearer YOUR_JWT_TOKEN
```

### Get Detailed Session with All Q&A
```
GET http://localhost:8000/api/interview/history/?session_id=SESSION_ID_FROM_STEP_3
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 🔍 Step 6: Check Interview Progress
```
GET http://localhost:8000/api/interview/progress/
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## 🧪 Testing Scenarios

### ✅ **Scenario 1: Happy Path**
1. Generate 3 questions → Get session_id
2. Submit 3 complete answers → Get evaluations
3. Check history → Verify data persistence

### ✅ **Scenario 2: Partial Answers**
1. Generate 5 questions
2. Submit only 3 answers → Should process available answers
3. Check response for partial completion

### ✅ **Scenario 3: Invalid Data**
1. Submit with invalid session_id → Should get 404
2. Submit empty answers array → Should get 400
3. Submit with non-existent question_id → Should skip invalid entries

### ✅ **Scenario 4: Different Difficulties**
Test with `"difficulty": "easy"`, `"medium"`, `"hard"`

### ✅ **Scenario 5: Different Question Counts**
Test with `"question_count": 3, 5, 10, 15`

---

## 🐛 Common Issues & Solutions

### **Issue: "User not found"**
- **Solution**: Ensure JWT token is valid and user exists in `sb_users` table

### **Issue: "No uploaded CV found"**
- **Solution**: Upload a CV first using `/api/rag/cv-upload/`

### **Issue: "Session not found"**
- **Solution**: Use the exact `session_id` returned from `/interview/questions/`

### **Issue: "FIREWORKS_API_KEY is not set"**
- **Solution**: Check environment variables in Django settings

### **Issue: "Model call failed"**
- **Solution**: Check Fireworks API key validity and network connection

---

## 📈 Expected Performance

- **Question Generation**: ~5-10 seconds for 5 questions
- **Batch Evaluation**: ~15-30 seconds for 5 answers (longer timeout: 120s)
- **History Retrieval**: <1 second

---

## 🎯 Success Criteria

✅ **Questions Generated**: Session created with unique IDs  
✅ **Answers Stored**: All valid answers saved to database  
✅ **AI Evaluation**: Comprehensive feedback with scores  
✅ **Data Persistence**: History API shows complete session  
✅ **Error Handling**: Graceful handling of invalid inputs  

---

## 📱 Postman Collection Export

Save these requests as a Postman collection for easy reuse:

1. **Interview - Generate Questions**
2. **Interview - Submit All Answers** 
3. **Interview - Get History**
4. **Interview - Get Session Details**
5. **Interview - Get Progress**

**Pro Tip**: Use Postman environment variables for `{{jwt_token}}` and `{{session_id}}` to make testing easier!
