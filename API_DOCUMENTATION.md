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
