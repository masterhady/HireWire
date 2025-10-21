# HireWire - AI-Powered Job Search Platform UI Specification

## 🎯 Project Overview
Build a modern, responsive web application for HireWire - an AI-powered job search platform that combines RAG (Retrieval-Augmented Generation) technology with comprehensive career development tools.

## 🏗️ Application Architecture

### Backend API Base URL
```
http://localhost:8080/api/
```

### Authentication
- JWT-based authentication
- Include `Authorization: Bearer <token>` in all API calls
- Token refresh functionality

---

## 📱 Core Pages & Features

### 1. **Authentication Pages**

#### **Login Page** (`/login`)
- **Design**: Clean, modern login form
- **Fields**: Username, Password
- **Features**: 
  - Remember me checkbox
  - Forgot password link
  - Register link
  - Social login buttons (optional)
- **API**: `POST /auth/login/`
- **Redirect**: Dashboard after successful login

#### **Register Page** (`/register`)
- **Design**: Multi-step registration form
- **Fields**: Username, Email, Password, First Name, Last Name, Role
- **Role Selection**: 
  - Job Seeker (default)
  - Company
  - Admin
- **Features**: Password strength indicator, terms acceptance
- **API**: `POST /auth/register/`

---

### 2. **Dashboard Page** (`/dashboard`)
- **Design**: Modern dashboard with cards and analytics
- **API**: `GET /dashboard/`
- **Key Metrics Cards**:
  - Job Matches Count
  - CV Score (AI-generated)
  - Profile Views
  - Top Job Matches (3 cards)
- **Layout**: Grid layout with responsive cards
- **Features**: Quick actions, recent activity

---

### 3. **CV Management Pages**

#### **CV Upload Page** (`/cv/upload`)
- **Design**: Drag-and-drop file upload interface
- **Supported Formats**: .txt, .pdf, .docx
- **Features**:
  - File validation
  - Progress indicator
  - Preview of uploaded content
  - Replace existing CV option
- **API**: `POST /rag/cv-upload/`
- **Validation**: CV format detection

#### **CV Recommendations Page** (`/cv/recommendations`)
- **Design**: Comprehensive CV analysis dashboard
- **API**: `POST /rag/cv-recommendations/`
- **Sections**:
  - **Overall Score**: Large score display with color coding
  - **Skills Match**: Progress bars for different skills
  - **Experience Relevance**: Timeline view
  - **ATS Readability**: Score with tips
  - **AI Suggestions**: Expandable list with actionable items
  - **Your CV Section**: Extracted CV information display
    - Name, Title, Experience, Skills, Contact info
- **Features**: Export recommendations, share functionality

---

### 4. **Job Search & Matching**

#### **Job Search Page** (`/jobs/search`)
- **Design**: Advanced search interface with filters
- **API**: `GET /rag/search/`
- **Features**:
  - Search bar with autocomplete
  - Location filter
  - Salary range slider
  - Company filter
  - Job type filter (full-time, part-time, contract)
  - Experience level filter
- **Results**: Card-based job listings with match scores

#### **Job Match Page** (`/jobs/match`)
- **Design**: AI-powered job matching results
- **API**: `POST /rag/cv-match/`
- **Features**:
  - Match percentage display
  - Detailed job cards
  - Filter by match score
  - Save/unsave jobs
  - Apply directly
- **Layout**: Grid of job cards with match indicators

#### **Job Details Page** (`/jobs/:id`)
- **Design**: Comprehensive job information
- **Features**:
  - Full job description
  - Company information
  - Requirements breakdown
  - Match analysis
  - Apply button
  - Save job option

---

### 5. **Career Development**

#### **Career Advisor Page** (`/career/advisor`)
- **Design**: AI-powered career guidance dashboard
- **API**: `POST /career-advisor/`
- **Sections**:
  - **Current Role Assessment**: AI analysis of current position
  - **Career Paths**: Interactive career path cards
    - Title, Description, Transition Difficulty, Growth Potential
  - **Skills Gaps**: Visual skills gap analysis
  - **Market Demand**: Job market insights with salary ranges
  - **Recommendations**: Actionable career advice
  - **Next Steps**: Prioritized action items
- **Features**: Export career plan, set goals

---

### 6. **Interview Preparation System**

#### **Interview Questions Generator** (`/interview/questions`)
- **Design**: Interactive question generation interface
- **API**: `POST /interview/questions/`
- **Features**:
  - Job description input
  - Difficulty selection (Easy/Medium/Hard)
  - Question count slider
  - Generate questions button
  - Question categories filter
- **Results**: Expandable question cards with tips

#### **Interview Practice Page** (`/interview/practice`)
- **Design**: Chat-style interview practice interface
- **API**: `POST /interview/practice/`
- **Features**:
  - Question display
  - Text area for answers
  - Submit answer button
  - AI feedback display
  - Follow-up questions
- **Layout**: Split-screen with question and answer sections

#### **Interview Evaluation Page** (`/interview/evaluate`)
- **Design**: Comprehensive answer evaluation
- **API**: `POST /interview/evaluate/`
- **Sections**:
  - **Overall Score**: Large score display
  - **Strengths**: Highlighted positive aspects
  - **Weaknesses**: Areas for improvement
  - **Correct Answer**: Ideal answer display
  - **Analysis**: Detailed feedback
  - **Improvement Tips**: Actionable suggestions
  - **Follow-up Questions**: Additional practice questions

#### **Interview History Page** (`/interview/history`)
- **Design**: Interview session management
- **API**: `GET /interview/history/`
- **Features**:
  - Session list with completion rates
  - Average scores per session
  - Detailed session view
  - Performance trends
  - Export interview history

#### **Interview Progress Page** (`/interview/progress`)
- **Design**: Analytics dashboard for interview performance
- **API**: `GET /interview/progress/`
- **Sections**:
  - **Overall Stats**: Total sessions, questions, answers, completion rate
  - **Category Performance**: Scores by question category
  - **Difficulty Performance**: Scores by difficulty level
  - **Performance Trend**: Chart showing improvement over time
- **Features**: Progress charts, performance insights

---

### 7. **User Profile & Settings**

#### **Profile Page** (`/profile`)
- **Design**: User profile management
- **Features**:
  - Personal information
  - CV management
  - Preferences
  - Account settings
- **API**: User management endpoints

#### **Settings Page** (`/settings`)
- **Design**: Application settings and preferences
- **Features**:
  - Notification preferences
  - Privacy settings
  - API key management
  - Theme selection

---

## 🎨 Design System

### **Color Palette**
- **Primary**: Modern blue (#3B82F6)
- **Secondary**: Professional green (#10B981)
- **Accent**: Orange for highlights (#F59E0B)
- **Success**: Green (#059669)
- **Warning**: Yellow (#D97706)
- **Error**: Red (#DC2626)
- **Neutral**: Gray scale (#F9FAFB to #111827)

### **Typography**
- **Headings**: Inter or Poppins (bold, modern)
- **Body**: Inter or system fonts (readable)
- **Code**: JetBrains Mono or Fira Code

### **Components**
- **Cards**: Rounded corners, subtle shadows
- **Buttons**: Modern, with hover effects
- **Forms**: Clean inputs with validation states
- **Charts**: Interactive, responsive
- **Modals**: Centered, with backdrop blur

### **Layout**
- **Responsive**: Mobile-first design
- **Grid**: CSS Grid and Flexbox
- **Spacing**: Consistent 8px grid system
- **Breakpoints**: Mobile (320px), Tablet (768px), Desktop (1024px+)

---

## 🔧 Technical Requirements

### **Frontend Framework**
- **React** with TypeScript
- **State Management**: Redux Toolkit or Zustand
- **Routing**: React Router v6
- **Styling**: Tailwind CSS or styled-components
- **HTTP Client**: Axios
- **Charts**: Chart.js or Recharts
- **Icons**: Heroicons or Lucide React

### **Key Features**
- **Responsive Design**: Mobile, tablet, desktop
- **Dark/Light Mode**: Theme switching
- **Loading States**: Skeleton loaders
- **Error Handling**: User-friendly error messages
- **Form Validation**: Real-time validation
- **File Upload**: Drag-and-drop with progress
- **Charts**: Interactive data visualization
- **Search**: Real-time search with debouncing
- **Pagination**: Efficient data loading

### **Authentication Flow**
- **Token Storage**: Secure localStorage/sessionStorage
- **Auto-refresh**: Automatic token renewal
- **Route Protection**: Private/public route handling
- **Logout**: Clear tokens and redirect

---

## 📊 Data Visualization

### **Dashboard Charts**
- **Performance Trends**: Line charts
- **Skill Analysis**: Radar charts
- **Category Performance**: Bar charts
- **Progress Tracking**: Progress bars and circles

### **Interview Analytics**
- **Score Distribution**: Histogram
- **Category Breakdown**: Pie charts
- **Improvement Trends**: Line charts
- **Difficulty Analysis**: Bar charts

---

## 🚀 User Experience

### **Navigation**
- **Sidebar**: Collapsible navigation
- **Breadcrumbs**: Clear page hierarchy
- **Quick Actions**: Floating action buttons
- **Search**: Global search functionality

### **Interactions**
- **Smooth Animations**: Framer Motion or CSS transitions
- **Loading States**: Skeleton screens
- **Feedback**: Toast notifications
- **Confirmation**: Modal dialogs for important actions

### **Accessibility**
- **WCAG 2.1 AA**: Compliance
- **Keyboard Navigation**: Full keyboard support
- **Screen Readers**: Proper ARIA labels
- **Color Contrast**: Sufficient contrast ratios

---

## 📱 Mobile Experience

### **Mobile-First Features**
- **Touch Gestures**: Swipe, pinch, tap
- **Responsive Images**: Optimized loading
- **Offline Support**: Service workers
- **Push Notifications**: Career updates

### **Progressive Web App**
- **Installable**: Add to home screen
- **Offline**: Basic functionality offline
- **Fast**: Optimized performance
- **Engaging**: Rich interactions

---

## 🔐 Security Considerations

### **Data Protection**
- **HTTPS**: Secure connections
- **Token Security**: Secure storage
- **Input Validation**: Client and server-side
- **XSS Protection**: Sanitized inputs

### **Privacy**
- **Data Minimization**: Only collect necessary data
- **User Control**: Data export/deletion
- **Transparency**: Clear privacy policy
- **Consent**: Explicit user consent

---

## 🎯 Success Metrics

### **User Engagement**
- **Session Duration**: Time spent on platform
- **Feature Usage**: Most used features
- **Return Rate**: User retention
- **Completion Rate**: Task completion

### **Performance**
- **Load Time**: < 3 seconds initial load
- **Responsiveness**: < 100ms interaction response
- **Accessibility**: 100% keyboard navigable
- **Mobile**: Perfect mobile experience

---

## 📋 Implementation Priority

### **Phase 1: Core Features**
1. Authentication (Login/Register)
2. Dashboard
3. CV Upload & Recommendations
4. Job Search & Matching

### **Phase 2: Advanced Features**
1. Career Advisor
2. Interview System
3. Progress Tracking
4. User Profile

### **Phase 3: Polish**
1. Advanced Analytics
2. Mobile Optimization
3. Performance Optimization
4. Accessibility Improvements

---

## 🎨 Visual Inspiration

### **Modern Design Trends**
- **Glassmorphism**: Subtle glass effects
- **Neumorphism**: Soft, tactile elements
- **Gradients**: Subtle color transitions
- **Micro-interactions**: Delightful animations

### **Professional Aesthetic**
- **Clean Layouts**: Plenty of white space
- **Consistent Spacing**: 8px grid system
- **Professional Colors**: Blue/green palette
- **Readable Typography**: Clear hierarchy

---

## 📞 API Integration Notes

### **Error Handling**
- **Network Errors**: Retry mechanisms
- **Validation Errors**: Field-specific messages
- **Server Errors**: User-friendly fallbacks
- **Timeout**: Graceful degradation

### **Loading States**
- **Skeleton Screens**: Content placeholders
- **Progress Indicators**: Upload progress
- **Spinners**: Loading animations
- **Optimistic Updates**: Immediate feedback

### **Caching Strategy**
- **API Responses**: Intelligent caching
- **User Data**: Persistent storage
- **Images**: Lazy loading
- **Assets**: CDN optimization

---

This specification provides a comprehensive guide for building a modern, AI-powered job search platform with all the features and functionality needed for a complete career development experience.
