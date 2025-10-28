# API Documentation

## Base URL
```
http://localhost:8080/api/
```

## Authentication
Most endpoints require JWT authentication. Include the access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

---

## Auth Endpoints

### 1. Register User
**POST** `/auth/register/`

**Description:** Create a new user account

**Authentication:** Not required

**Request Body:**
```json
{
  "username": "string (required)",
  "password": "string (required, min 8 chars)",
  "email": "string (optional)",
  "first_name": "string (optional)",
  "last_name": "string (optional)",
  "role": "string (optional, default: 'jobseeker')"
}
```

**Valid Roles:**
- `admin`
- `company`
- `jobseeker`

**Example Request:**
```bash
curl -X POST http://localhost:8080/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "company"
  }'
```

**Response:**
```json
{
  "message": "User registered successfully"
}
```

**Status Codes:**
- `201` - Created successfully
- `400` - Bad request (validation errors)

---

### 2. Login User
**POST** `/auth/login/`

**Description:** Authenticate user and get JWT tokens

**Authentication:** Not required

**Request Body:**
```json
{
  "username": "string (required)",
  "password": "string (required)"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8080/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "SecurePass123"
  }'
```

**Response:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "company"
  }
}
```

**Status Codes:**
- `200` - Login successful
- `401` - Invalid credentials

---

### 3. Refresh Token
**POST** `/auth/token/refresh/`

**Description:** Get new access token using refresh token

**Authentication:** Not required

**Request Body:**
```json
{
  "refresh": "string (required)"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8080/api/auth/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
  }'
```

**Response:**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Status Codes:**
- `200` - Token refreshed successfully
- `401` - Invalid refresh token

---

## Supabase Data Endpoints

### Companies

#### List Companies
**GET** `/companies/`

**Description:** Get all companies

**Authentication:** Required

**Query Parameters:**
- `page` (optional) - Page number for pagination
- `page_size` (optional) - Number of items per page

**Example Request:**
```bash
curl -X GET http://localhost:8080/api/companies/ \
  -H "Authorization: Bearer <access_token>"
```

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Tech Corp",
    "website": "https://techcorp.com",
    "location": "New York",
    "created_at": "2025-01-01T00:00:00Z"
  }
]
```

#### Create Company
**POST** `/companies/`

**Description:** Create a new company

**Authentication:** Required

**Request Body:**
```json
{
  "name": "string (required)",
  "website": "string (optional)",
  "location": "string (optional)",
  "created_at": "datetime (required)"
}
```

#### Get Company
**GET** `/companies/{id}/`

**Description:** Get specific company by ID

**Authentication:** Required

#### Update Company
**PUT/PATCH** `/companies/{id}/`

**Description:** Update company information

**Authentication:** Required

#### Delete Company
**DELETE** `/companies/{id}/`

**Description:** Delete a company

**Authentication:** Required

---

### Skills

#### List Skills
**GET** `/skills/`

**Description:** Get all skills

**Authentication:** Not required (public read access)

**Example Request:**
```bash
curl -X GET http://localhost:8080/api/skills/
```

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "Python"
  },
  {
    "id": "uuid",
    "name": "Django"
  }
]
```

#### Create Skill
**POST** `/skills/`

**Description:** Create a new skill

**Authentication:** Required

**Request Body:**
```json
{
  "name": "string (required)"
}
```

#### Get Skill
**GET** `/skills/{id}/`

**Description:** Get specific skill by ID

**Authentication:** Not required (public read access)

#### Update Skill
**PUT/PATCH** `/skills/{id}/`

**Description:** Update skill information

**Authentication:** Required

#### Delete Skill
**DELETE** `/skills/{id}/`

**Description:** Delete a skill

**Authentication:** Required

---

### Jobs

#### List Jobs
**GET** `/jobs/`

**Description:** Get all jobs

**Authentication:** Required

**Query Parameters:**
- `page` (optional) - Page number for pagination
- `page_size` (optional) - Number of items per page
- `is_active` (optional) - Filter by active status

**Example Request:**
```bash
curl -X GET http://localhost:8080/api/jobs/ \
  -H "Authorization: Bearer <access_token>"
```

**Response:**
```json
[
  {
    "id": "uuid",
    "company": "uuid",
    "title": "Software Engineer",
    "description": "Job description...",
    "requirements": "Job requirements...",
    "posted_at": "2025-01-01T00:00:00Z",
    "is_active": true
  }
]
```

#### Create Job
**POST** `/jobs/`

**Description:** Create a new job

**Authentication:** Required

**Request Body:**
```json
{
  "company": "uuid (required)",
  "title": "string (required)",
  "description": "string (optional)",
  "requirements": "string (optional)",
  "posted_at": "datetime (required)",
  "is_active": "boolean (required)"
}
```

#### Get Job
**GET** `/jobs/{id}/`

**Description:** Get specific job by ID

**Authentication:** Required

#### Update Job
**PUT/PATCH** `/jobs/{id}/`

**Description:** Update job information

**Authentication:** Required

#### Delete Job
**DELETE** `/jobs/{id}/`

**Description:** Delete a job

**Authentication:** Required

#### Add Skill to Job
**POST** `/jobs/{id}/skills/`

**Description:** Add a skill to a job

**Authentication:** Required

**Request Body:**
```json
{
  "skill_id": "uuid (required)"
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8080/api/jobs/{job_id}/skills/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "skill_id": "skill-uuid-here"
  }'
```

#### Remove Skill from Job
**DELETE** `/jobs/{id}/skills/{skill_id}/`

**Description:** Remove a skill from a job

**Authentication:** Required

**Example Request:**
```bash
curl -X DELETE http://localhost:8080/api/jobs/{job_id}/skills/{skill_id}/ \
  -H "Authorization: Bearer <access_token>"
```

---

## Interview Storage APIs

### Interview Answer Submission API

#### Submit Answer
**POST** `/interview/submit-answer/`

**Description:** Submit a user's answer to an interview question for storage.

**Authentication:** Required (JWT token)

**Request Body:**
```json
{
  "question_id": "uuid-of-interview-question",
  "user_answer": "I led a team of 5 developers to build a microservices architecture..."
}
```

**Response:**
```json
{
  "answer_id": "uuid",
  "question_id": "uuid",
  "user_answer": "string",
  "submitted_at": "2024-01-15T10:30:00Z"
}
```

**cURL Example:**
```bash
curl -X POST http://localhost:8000/api/interview/submit-answer/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_answer": "I led a team of 5 developers to build a microservices architecture that improved system performance by 40%"
  }'
```

### Interview History API

#### Get Interview History
**GET** `/interview/history/`

**Description:** Get user's interview history and progress.

**Authentication:** Required (JWT token)

**Query Parameters:**
- `limit` (optional): Number of sessions to return (default: 10)
- `session_id` (optional): Get specific session details

**Response (Summary):**
```json
{
  "sessions": [
    {
      "id": "uuid",
      "user": "uuid",
      "job_description": "string",
      "difficulty": "string",
      "created_at": "2024-01-15T10:30:00Z",
      "question_count": 5,
      "answered_questions": 3,
      "completion_rate": 60.0,
      "average_score": 85.5
    }
  ],
  "total_sessions": 10
}
```

**Response (Session Details):**
```json
{
  "session": {
    "id": "uuid",
    "user": "uuid",
    "job_description": "string",
    "difficulty": "string",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "questions": [
    {
      "id": "uuid",
      "session": "uuid",
      "question": "string",
      "category": "string",
      "difficulty": "string",
      "tips": "string",
      "expected_answer_focus": "string",
      "created_at": "2024-01-15T10:30:00Z",
      "answers": [
        {
          "id": "uuid",
          "question": "uuid",
          "user_answer": "string",
          "submitted_at": "2024-01-15T10:30:00Z",
          "evaluation": {
            "id": "uuid",
            "answer": "uuid",
            "overall_score": 85,
            "strengths": ["string"],
            "weaknesses": ["string"],
            "correct_answer": "string",
            "answer_analysis": "string",
            "improvement_tips": ["string"],
            "follow_up_questions": ["string"],
            "evaluated_at": "2024-01-15T10:30:00Z"
          }
        }
      ]
    }
  ]
}
```

**cURL Examples:**
```bash
# Get recent sessions summary
curl -X GET "http://localhost:8000/api/interview/history/?limit=5" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# Get specific session details
curl -X GET "http://localhost:8000/api/interview/history/?session_id=123e4567-e89b-12d3-a456-426614174000" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Interview Progress API

#### Get Interview Progress
**GET** `/interview/progress/`

**Description:** Get user's overall interview progress and statistics.

**Authentication:** Required (JWT token)

**Response:**
```json
{
  "overall_stats": {
    "total_sessions": 10,
    "total_questions": 50,
    "total_answers": 35,
    "completion_rate": 70.0
  },
  "category_performance": {
    "Technical": 85.5,
    "Behavioral": 78.2,
    "Leadership": 82.1
  },
  "difficulty_performance": {
    "easy": 90.0,
    "medium": 82.5,
    "hard": 75.0
  },
  "performance_trend": [
    {
      "session_id": "uuid",
      "date": "2024-01-15T10:30:00Z",
      "average_score": 85.5,
      "question_count": 5
    }
  ]
}
```

**cURL Example:**
```bash
curl -X GET http://localhost:8000/api/interview/progress/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

### CVs

#### List CVs
**GET** `/cvs/`

**Description:** Get all CVs

**Authentication:** Required

**Response:**
```json
[
  {
    "id": "uuid",
    "user": "uuid",
    "filename": "resume.pdf",
    "parsed_text": "Extracted text content...",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-01T00:00:00Z"
  }
]
```

#### Create CV
**POST** `/cvs/`

**Description:** Upload a new CV

**Authentication:** Required

**Request Body:**
```json
{
  "user": "uuid (required)",
  "filename": "string (required)",
  "parsed_text": "string (optional)",
  "created_at": "datetime (required)",
  "updated_at": "datetime (required)"
}
```

#### Get CV
**GET** `/cvs/{id}/`

**Description:** Get specific CV by ID

**Authentication:** Required

#### Update CV
**PUT/PATCH** `/cvs/{id}/`

**Description:** Update CV information

**Authentication:** Required

#### Delete CV
**DELETE** `/cvs/{id}/`

**Description:** Delete a CV

**Authentication:** Required

---

### Applications

#### List Applications
**GET** `/applications/`

**Description:** Get all applications

**Authentication:** Required

**Response:**
```json
[
  {
    "id": "uuid",
    "cv": "uuid",
    "job": "uuid",
    "company": "uuid",
    "match_score": "0.8500",
    "matched_at": "2025-01-01T00:00:00Z"
  }
]
```

#### Create Application
**POST** `/applications/`

**Description:** Create a new job application

**Authentication:** Required

**Request Body:**
```json
{
  "cv": "uuid (required)",
  "job": "uuid (required)",
  "company": "uuid (required)",
  "match_score": "decimal (optional)",
  "matched_at": "datetime (optional)"
}
```

#### Get Application
**GET** `/applications/{id}/`

**Description:** Get specific application by ID

**Authentication:** Required

#### Update Application
**PUT/PATCH** `/applications/{id}/`

**Description:** Update application information

**Authentication:** Required

#### Delete Application
**DELETE** `/applications/{id}/`

**Description:** Delete an application

**Authentication:** Required

---

### Read-Only Endpoints

#### CV Embeddings
**GET** `/cv-embeddings/`
**GET** `/cv-embeddings/{id}/`

**Description:** Get CV embeddings (read-only)

**Authentication:** Required

#### Job Embeddings
**GET** `/job-embeddings/`
**GET** `/job-embeddings/{id}/`

**Description:** Get job embeddings (read-only)

**Authentication:** Required

#### Recommendations
**GET** `/recommendations/`
**GET** `/recommendations/{id}/`

**Description:** Get recommendations (read-only)

**Authentication:** Required

#### Supabase Users
**GET** `/sb-users/`
**POST** `/sb-users/`
**GET** `/sb-users/{id}/`
**PUT/PATCH** `/sb-users/{id}/`
**DELETE** `/sb-users/{id}/`

**Description:** Manage Supabase users (separate from Django auth)

**Authentication:** Required

---

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "detail": "A server error occurred."
}
```

---

## Testing the API

### Using cURL
```bash
# Set your access token
export ACCESS_TOKEN="your_access_token_here"

# Test protected endpoint
curl -X GET http://localhost:8080/api/companies/ \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

### Using Postman
1. Set base URL: `http://localhost:8080/api/`
2. For protected endpoints, add header:
   - Key: `Authorization`
   - Value: `Bearer <your_access_token>`
3. For POST/PUT requests, set Content-Type to `application/json`

---

## Notes

- All timestamps are in ISO 8601 format
- UUIDs are used for all primary keys
- Pagination is available for list endpoints
- Vector embeddings are read-only and returned as JSON
- The `job_skills` relationship is managed through the job endpoints
- Public endpoints: register, login, token refresh, and GET skills
- All other endpoints require JWT authentication

---

## RAG and CV Endpoints (New)

### RAG Text Search
**POST** `/rag/search/`

**Description:** Retrieve similar jobs for a free-text query using vector search. Optionally returns an AI summary if configured.

**Authentication:** Not required

**Request Body:**
```json
{
  "query": "string (required)",
  "top_n": 10,
  "similarity_threshold": 0.35,
  "must_contain": ["django", "postgres"],
  "must_not_contain": ["intern"]
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/api/rag/search/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "senior backend engineer python django postgres",
    "top_n": 10,
    "similarity_threshold": 0.35
  }'
```

---

### Upload/Upsert CV
**POST** `/rag/cv-upload/`

**Description:** Upload or update the authenticated user's single CV. Parses `.txt`, `.pdf`, `.docx`; stores text in `cvs` and chunk embeddings in `cv_embeddings`.

**Authentication:** Required

**Body (multipart or JSON):**
```json
{
  "cv_text": "string (optional if file provided)",
  "filename": "string (optional)"
}
```

**Notes:**
- If a CV already exists for the user, it will be updated and its embeddings replaced.
- Non-CV content is rejected with 415.

**Examples:**
```bash
# File upload
curl -X POST http://localhost:8080/api/rag/cv-upload/ \
  -H "Authorization: Bearer <access_token>" \
  -F "file=@/path/to/resume.pdf"

# Raw text
curl -X POST http://localhost:8080/api/rag/cv-upload/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"cv_text":"...","filename":"resume.txt"}'
```

---

### CV Match (by stored CV or text)
**POST** `/rag/cv-match/`

**Description:** Find best-matching jobs for a CV. Uses the provided `cv_id` or `cv_text`. If neither is provided, uses the latest uploaded CV of the authenticated user.

**Authentication:** Required

**Request Body:**
```json
{
  "cv_id": "uuid (optional)",
  "cv_text": "string (optional)",
  "top_n": 10,
  "similarity_threshold": 0.3,
  "must_contain": ["python"],
  "must_not_contain": ["intern"]
}
```

**Examples:**
```bash
# Use latest uploaded CV automatically
curl -X POST http://localhost:8080/api/rag/cv-match/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"top_n": 10, "similarity_threshold": 0.3}'

# Use specific stored CV
curl -X POST http://localhost:8080/api/rag/cv-match/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"<cv_uuid>", "top_n": 10}'

# Ad-hoc text (no storage)
curl -X POST http://localhost:8080/api/rag/cv-match/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"cv_text":"raw resume text here"}'
```

---

### CV Recommendations (AI)
**POST** `/rag/cv-recommendations/`

**Description:** Uses Fireworks chat model to generate CV scores, tailored suggestions, and a structured CV extract for UI display.

**Authentication:** Required

**Request Body:**
```json
{
  "cv_id": "uuid (optional)",
  "cv_text": "string (optional)"
}
```

**Response (fields):**
- `overall_score`, `skills_match`, `experience_relevance`, `ats_readability`
- `suggestions`: list of `{title, priority, details}`
- `cv_extract`: `{ full_name, job_title, summary, skills[], experience[], contact{} }`

**Examples:**
```bash
# Latest CV
curl -X POST http://localhost:8080/api/rag/cv-recommendations/ \
  -H "Authorization: Bearer <access_token>"

# Specific CV
curl -X POST http://localhost:8080/api/rag/cv-recommendations/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"<cv_uuid>"}'

# Raw text
curl -X POST http://localhost:8080/api/rag/cv-recommendations/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"cv_text":"..."}'
```

---

### Dashboard Aggregate (New)
**GET** `/dashboard/`

**Description:** Returns data for the dashboard cards and lists: total job matches from the latest CV, AI CV score, placeholder profile views, and top 3 matches.

**Authentication:** Required

**Example:**
```bash
curl -X GET http://localhost:8080/api/dashboard/ \
  -H "Authorization: Bearer <access_token>"
```

---

### Career Advisor AI Agent (New)
**POST** `/career-advisor/`

**Description:** AI-powered career guidance that analyzes the user's CV and provides personalized career path recommendations, skills gaps, market demand insights, and actionable next steps.

**Authentication:** Required

**Request Body:**
```json
{
  "cv_id": "uuid (optional)",
  "cv_text": "string (optional)"
}
```

**Response Fields:**
- `current_role_assessment`: Brief assessment of current position
- `career_paths`: Array of career options with title, description, transition_difficulty, growth_potential
- `skills_gaps`: Array of missing skills to develop
- `market_demand`: Array of roles with demand_level and salary_range
- `recommendations`: Array of specific improvement suggestions
- `next_steps`: Array of actionable next steps

**Examples:**
```bash
# Use latest uploaded CV automatically
curl -X POST http://localhost:8080/api/career-advisor/ \
  -H "Authorization: Bearer <access_token>"

# Use specific stored CV
curl -X POST http://localhost:8080/api/career-advisor/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"cv_id":"<cv_uuid>"}'

# Analyze raw text
curl -X POST http://localhost:8080/api/career-advisor/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"cv_text":"..."}'
```

**Example Response:**
```json
{
  "current_role_assessment": "Experienced frontend developer with strong React skills",
  "career_paths": [
    {
      "title": "Senior Frontend Architect",
      "description": "Lead technical decisions and mentor junior developers",
      "transition_difficulty": "low",
      "growth_potential": "high"
    },
    {
      "title": "Full Stack Developer",
      "description": "Expand into backend development with Node.js/Python",
      "transition_difficulty": "medium",
      "growth_potential": "high"
    }
  ],
  "skills_gaps": ["TypeScript", "GraphQL", "Docker"],
  "market_demand": [
    {
      "role": "Senior Frontend Developer",
      "demand_level": "high",
      "salary_range": "$80k-120k"
    }
  ],
  "recommendations": [
    "Learn TypeScript for better code quality",
    "Get certified in cloud platforms (AWS/Azure)",
    "Build a portfolio with full-stack projects"
  ],
  "next_steps": [
    "Update LinkedIn with new skills",
    "Apply to 10 senior frontend positions",
    "Start learning TypeScript this month"
  ]
}
```

---

### Interview Questions Generator (New)
**POST** `/interview/questions/`

**Description:** Generate personalized interview questions based on the user's CV and target job description using AI.

**Authentication:** Required

**Request Body:**
```json
{
  "job_description": "string (required)",
  "cv_id": "uuid (optional)",
  "cv_text": "string (optional)",
  "question_count": 10,
  "difficulty": "medium"
}
```

**Response Fields:**
- `session_id`: Interview session UUID for tracking
- `questions`: Array of question objects with id, question, category, difficulty, tips, expected_answer_focus
- `job_description`: The target job description
- `difficulty`: Selected difficulty level
- `question_count`: Number of questions generated
- `instructions`: Instructions for the batch processing flow
- `flow`: Set to "batch_processing" to indicate the new flow

**Examples:**
```bash
# Generate questions for a specific job
curl -X POST http://localhost:8080/api/interview/questions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Senior Frontend Developer with React, TypeScript, and 5+ years experience...",
    "question_count": 15,
    "difficulty": "hard"
  }'

# Use specific CV
curl -X POST http://localhost:8080/api/interview/questions/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_description": "Data Scientist position...",
    "cv_id": "<cv_uuid>",
    "difficulty": "medium"
  }'
```

**Example Response:**
```json
{
  "session_id": "session-uuid-here",
  "questions": [
    {
      "id": "question-1-uuid",
      "question": "Tell me about a challenging React project you worked on and how you solved performance issues",
      "category": "technical",
      "difficulty": "hard",
      "tips": "Focus on specific metrics and optimization techniques",
      "expected_answer_focus": "problem-solving, technical depth, and measurable results"
    },
    {
      "id": "question-2-uuid",
      "question": "How do you handle state management in large React applications?",
      "category": "technical",
      "difficulty": "medium",
      "tips": "Discuss Redux, Context API, or other state management solutions",
      "expected_answer_focus": "architecture decisions and scalability considerations"
    }
  ],
  "job_description": "Senior Frontend Developer...",
  "difficulty": "hard",
  "question_count": 2,
  "instructions": "Answer all questions, then use /api/interview/submit-all-answers/ to submit all answers for batch evaluation.",
  "flow": "batch_processing"
}
```

---

### Interview Practice Chat (New)
**POST** `/interview/practice/`

**Description:** Chat-style interview practice where users can submit answers and receive AI feedback with scores and suggestions.

**Authentication:** Required

**Request Body:**
```json
{
  "question": "string (required)",
  "answer": "string (required)",
  "cv_id": "uuid (optional)",
  "cv_text": "string (optional)",
  "job_description": "string (optional)"
}
```

**Response Fields:**
- `overall_score`: Score from 0-100
- `strengths`: Array of positive aspects
- `areas_for_improvement`: Array of areas to work on
- `follow_up_question`: Suggested follow-up question
- `detailed_feedback`: Comprehensive feedback text
- `question`: The original question
- `answer`: The submitted answer

**Examples:**
```bash
# Practice with feedback
curl -X POST http://localhost:8080/api/interview/practice/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me about a challenging project you worked on",
    "answer": "I worked on a React application that had performance issues. I optimized the bundle size and implemented code splitting...",
    "job_description": "Senior Frontend Developer role..."
  }'

# Practice with CV context
curl -X POST http://localhost:8080/api/interview/practice/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is your experience with TypeScript?",
    "answer": "I have been using TypeScript for 2 years...",
    "cv_id": "<cv_uuid>"
  }'
```

**Example Response:**
```json
{
  "overall_score": 78,
  "strengths": [
    "Good use of specific technical details",
    "Clear explanation of the problem and solution",
    "Mentioned measurable improvements"
  ],
  "areas_for_improvement": [
    "Could include more details about team collaboration",
    "Missing information about lessons learned",
    "Consider adding quantifiable business impact"
  ],
  "follow_up_question": "What specific metrics did you use to measure the performance improvements?",
  "detailed_feedback": "Your answer demonstrates strong technical knowledge and problem-solving skills. The explanation of code splitting and bundle optimization shows deep understanding. To strengthen your response, consider adding more context about team dynamics and the broader business impact of your work.",
  "question": "Tell me about a challenging project you worked on",
  "answer": "I worked on a React application that had performance issues..."
}
```

---

### Interview Answer Evaluation (New)
**POST** `/interview/evaluate/`

**Description:** Evaluate user's answer to interview questions and provide the correct/ideal answer with detailed feedback and improvement tips.

**Authentication:** Required

**Request Body:**
```json
{
  "question": "string (required)",
  "user_answer": "string (required)",
  "cv_id": "uuid (optional)",
  "cv_text": "string (optional)",
  "job_description": "string (optional)"
}
```

**Response Fields:**
- `overall_score`: Score from 0-100
- `strengths`: Array of positive aspects in the answer
- `weaknesses`: Array of areas that need improvement
- `correct_answer`: The ideal/perfect answer to the question
- `answer_analysis`: Detailed analysis of the user's answer
- `improvement_tips`: Specific tips to improve future answers
- `follow_up_questions`: Suggested follow-up questions for practice
- `question`: The original question
- `user_answer`: The submitted answer

**Examples:**
```bash
# Evaluate answer with CV context
curl -X POST http://localhost:8080/api/interview/evaluate/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Tell me about a challenging project you worked on",
    "user_answer": "I worked on a React app that was slow. I optimized it by using code splitting and lazy loading.",
    "job_description": "Senior Frontend Developer role..."
  }'

# Evaluate with specific CV
curl -X POST http://localhost:8080/api/interview/evaluate/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "How do you handle state management in React?",
    "user_answer": "I use Redux for complex apps and Context API for simple state.",
    "cv_id": "<cv_uuid>"
  }'
```

**Example Response:**
```json
{
  "overall_score": 72,
  "strengths": [
    "Good technical knowledge of React optimization",
    "Mentioned specific techniques (code splitting, lazy loading)",
    "Clear and concise communication"
  ],
  "weaknesses": [
    "Missing specific metrics or results",
    "No mention of challenges faced",
    "Could include team collaboration aspects"
  ],
  "correct_answer": "The ideal answer would include: 1) Specific project context and your role, 2) The challenge you faced (e.g., 'bundle size was 2MB, load time 8 seconds'), 3) Your solution with technical details, 4) Quantifiable results ('reduced bundle to 800KB, load time to 2 seconds'), 5) What you learned and how it helped the team/business.",
  "answer_analysis": "Your answer shows good technical understanding and mentions relevant optimization techniques. However, it lacks specific details about the project scope, your role, the impact of your work, and the challenges you overcame. A stronger answer would include metrics and business impact.",
  "improvement_tips": [
    "Use the STAR method (Situation, Task, Action, Result)",
    "Include specific numbers and metrics",
    "Mention your role and responsibilities",
    "Describe challenges and how you overcame them",
    "Connect your work to business outcomes"
  ],
  "follow_up_questions": [
    "What was the most challenging part of that optimization project?",
    "How did you measure the performance improvements?",
    "What would you do differently if you had to do it again?",
    "How did this project impact your team or the business?"
  ],
  "question": "Tell me about a challenging project you worked on",
  "user_answer": "I worked on a React app that was slow. I optimized it by using code splitting and lazy loading."
}
```

---

### Interview Batch Submission API (New)
**POST** `/interview/submit-all-answers/`

**Description:** Submit all answers for an interview session and receive comprehensive batch AI evaluation. This is the recommended approach for realistic interview simulation - generate all questions first, collect all answers, then evaluate everything together for holistic feedback.

**Authentication:** Required

**Request Body:**
```json
{
  "session_id": "uuid (required)",
  "answers": [
    {
      "question_id": "uuid (required)",
      "user_answer": "string (required)"
    }
  ]
}
```

**Response Fields:**
- `session_id`: Interview session UUID
- `total_questions`: Number of questions in the session
- `total_evaluations`: Number of answers evaluated
- `average_score`: Overall session score (0-100)
- `evaluations`: Array of detailed evaluations for each answer
- `session_complete`: Boolean indicating if session is complete
- `message`: Success message

**Examples:**
```bash
# Submit all answers for batch evaluation
curl -X POST http://localhost:8080/api/interview/submit-all-answers/ \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session-uuid-here",
    "answers": [
      {
        "question_id": "question-1-uuid",
        "user_answer": "I led a team of 5 developers to build a microservices architecture that reduced system latency by 40% and improved scalability to handle 10x more users..."
      },
      {
        "question_id": "question-2-uuid", 
        "user_answer": "For state management in large React applications, I prefer Redux Toolkit with RTK Query for complex apps, but Context API for simpler state needs..."
      },
      {
        "question_id": "question-3-uuid",
        "user_answer": "My biggest challenge was migrating a legacy monolith to microservices while maintaining zero downtime. I used the strangler fig pattern..."
      }
    ]
  }'
```

**Example Response:**
```json
{
  "session_id": "session-uuid-here",
  "total_questions": 3,
  "total_evaluations": 3,
  "average_score": 82.3,
  "evaluations": [
    {
      "evaluation_id": "eval-1-uuid",
      "answer_id": "answer-1-uuid",
      "question_id": "question-1-uuid",
      "question": "Tell me about a challenging project you led",
      "user_answer": "I led a team of 5 developers...",
      "evaluation": {
        "overall_score": 85,
        "strengths": ["Clear leadership example", "Quantifiable results", "Technical depth"],
        "weaknesses": ["Could elaborate on team challenges", "Missing stakeholder management"],
        "correct_answer": "The ideal answer would include specific project context, team dynamics, challenges faced, your leadership approach, technical decisions, and measurable business impact...",
        "answer_analysis": "Strong technical leadership example with good metrics. Shows clear impact and technical understanding. Could be enhanced with more details about team management and stakeholder communication.",
        "improvement_tips": ["Add details about team challenges and how you handled them", "Include stakeholder management aspects", "Mention lessons learned"],
        "follow_up_questions": ["How did you handle conflicts within the team?", "What was the business impact of this project?"]
      }
    }
  ],
  "session_complete": true,
  "message": "All answers evaluated successfully using batch AI processing"
}
```

**Recommended Interview Flow:**
1. **Generate Questions**: `POST /interview/questions/` - Get all questions for the session
2. **Collect Answers**: User answers all questions (store locally or use individual submission)
3. **Batch Evaluation**: `POST /interview/submit-all-answers/` - Submit all answers for comprehensive evaluation
4. **Review Results**: Use the detailed evaluations for learning and improvement
