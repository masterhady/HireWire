
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .supabase_test import test_supabase_connection
from .auth_views import RegisterView, LoginView
from .supabase_views import (
    CompanyViewSet,
    SbUserViewSet,
    SkillViewSet,
    CVViewSet,
    CVEmbeddingViewSet,
    JobViewSet,
    JobEmbeddingViewSet,
    ApplicationViewSet,
    RecommendationViewSet,
    CoverLetterViewSet,
    RAGSearchView,
    CVMatchView,
    CVUploadView,
    CVRecommendationsView,
    CVRewriteView,
    DashboardView,
    CareerAdvisorView,
    MultiAgentCareerView,
    InterviewQuestionsView,
    InterviewPracticeView,
    InterviewAnswerEvaluationView,
    InterviewAnswerSubmissionView,
    InterviewBatchSubmissionView,
    InterviewHistoryView,
    InterviewProgressView,
    AudioInterviewQuestionsView,
    AudioInterviewQuestionAudioView,
    AudioInterviewAnswerSubmissionView,
    AudioInterviewBatchSubmissionView,
    AudioInterviewEvaluationView,
    AudioInterviewSessionEvaluationsView,
    AudioInterviewHistoryView,
    VoiceChatTurnView,
    VoiceChatEvaluateView,
    TechVoiceChatTurnView,
    TechVoiceChatEvaluateView,
    OpenAIConversationalInterviewView,
)
from .resume_views import (
    ResumeViewSet, WorkExperienceViewSet, EducationViewSet, 
    ResumeSkillViewSet, ResumeProjectViewSet
)
from .video_interview_views import VideoInterviewViewSet
from .analytics_views import AnalyticsViewSet
from .views.coding_profile_views import CodingProfileViewSet
from .views.company_coding_analysis_views import CompanyLeetCodeAnalysisView, CompanyLeetCodeExportView
from .views.employee_progress_views import (
    EmployeeViewSet, EmployeeProgressView, KPIDashboardView, SyncEmployeeView
)
from .views.employee_goal_views import EmployeeGoalViewSet

router = DefaultRouter()
router.register(r"companies", CompanyViewSet, basename="companies")
router.register(r"sb-users", SbUserViewSet, basename="sb-users")
router.register(r"skills", SkillViewSet, basename="skills")
router.register(r"cvs", CVViewSet, basename="cvs")
router.register(r"cv-embeddings", CVEmbeddingViewSet, basename="cv-embeddings")
router.register(r"jobs", JobViewSet, basename="jobs")
router.register(r"job-embeddings", JobEmbeddingViewSet, basename="job-embeddings")
router.register(r"applications", ApplicationViewSet, basename="applications")
router.register(r"recommendations", RecommendationViewSet, basename="recommendations")
router.register(r"cover-letters", CoverLetterViewSet, basename="cover-letters")
router.register(r"resumes", ResumeViewSet, basename="resumes")
router.register(r"resume-experience", WorkExperienceViewSet, basename="resume-experience")
router.register(r"resume-education", EducationViewSet, basename="resume-education")
router.register(r"resume-skills", ResumeSkillViewSet, basename="resume-skills")
router.register(r"resume-projects", ResumeProjectViewSet, basename="resume-projects")
router.register(r"video-interviews", VideoInterviewViewSet, basename="video-interviews")
router.register(r'analytics', AnalyticsViewSet, basename='analytics')
router.register(r'coding-profiles', CodingProfileViewSet, basename='coding-profiles')

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth_register"),
    path("auth/login/", LoginView.as_view(), name="auth_login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("test-supabase/", test_supabase_connection, name="test_supabase_connection"),
    path("rag/search/", RAGSearchView.as_view(), name="rag_search"),
    path("rag/cv-match/", CVMatchView.as_view(), name="rag_cv_match"),
    path("rag/cv-upload/", CVUploadView.as_view(), name="rag_cv_upload"),
    path("rag/cv-recommendations/", CVRecommendationsView.as_view(), name="rag_cv_recommendations"),
    path("rag/cv-generate/", CVRewriteView.as_view(), name="rag_cv_rewrite"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("career-advisor/", CareerAdvisorView.as_view(), name="career_advisor"),
    path("multi-agent-career/", MultiAgentCareerView.as_view(), name="multi_agent_career"),
    path("interview/questions/", InterviewQuestionsView.as_view(), name="interview_questions"),
    path("interview/practice/", InterviewPracticeView.as_view(), name="interview_practice"),
    path("interview/evaluate/", InterviewAnswerEvaluationView.as_view(), name="interview_evaluate"),
    path("interview/submit-answer/", InterviewAnswerSubmissionView.as_view(), name="interview_submit_answer"),
    path("interview/submit-all-answers/", InterviewBatchSubmissionView.as_view(), name="interview_batch_submission"),
    path("interview/history/", InterviewHistoryView.as_view(), name="interview_history"),
    path("interview/progress/", InterviewProgressView.as_view(), name="interview_progress"),
    # Audio Interview APIs
    path("audio-interview/questions/", AudioInterviewQuestionsView.as_view(), name="audio_interview_questions"),
    path("audio-interview/question/<uuid:question_id>/audio/", AudioInterviewQuestionAudioView.as_view(), name="audio_interview_question_audio"),
    path("audio-interview/submit-answer/", AudioInterviewAnswerSubmissionView.as_view(), name="audio_interview_submit_answer"),
    path("audio-interview/submit-all-answers/", AudioInterviewBatchSubmissionView.as_view(), name="audio_interview_batch_submission"),
    path("audio-interview/evaluation/<uuid:answer_id>/", AudioInterviewEvaluationView.as_view(), name="audio_interview_evaluation"),
    path("audio-interview/session/<uuid:session_id>/evaluations/", AudioInterviewSessionEvaluationsView.as_view(), name="audio_interview_session_evaluations"),
    path("audio-interview/history/", AudioInterviewHistoryView.as_view(), name="audio_interview_history"),
    # Voice chat (conversational HR)
    path("voice-chat/turn/", VoiceChatTurnView.as_view(), name="voice_chat_turn"),
    path("voice-chat/evaluate/", VoiceChatEvaluateView.as_view(), name="voice_chat_evaluate"),
    path("tech-voice-chat/turn/", TechVoiceChatTurnView.as_view(), name="tech_voice_chat_turn"),
    path("tech-voice-chat/evaluate/", TechVoiceChatEvaluateView.as_view(), name="tech_voice_chat_evaluate"),
    # OpenAI Conversational Interview (ChatGPT-style voice chat)
    path("openai-interview/turn/", OpenAIConversationalInterviewView.as_view(), name="openai_interview_turn"),
    # Company LeetCode Analysis
    path("company/leetcode/analyze/", CompanyLeetCodeAnalysisView.as_view(), name="company_leetcode_analyze"),
    path("company/leetcode/export/", CompanyLeetCodeExportView.as_view(), name="company_leetcode_export"),
    # Employee Management & Progress Tracking
    path("company/employees/", EmployeeViewSet.as_view(), name="company_employees"),
    path("company/employees/<uuid:employee_id>/", EmployeeViewSet.as_view(), name="company_employee_detail"),
    path("company/employees/<uuid:employee_id>/sync/", SyncEmployeeView.as_view(), name="company_employee_sync"),
    path("company/employees/<uuid:employee_id>/progress/", EmployeeProgressView.as_view(), name="company_employee_progress"),
    path("company/progress/", EmployeeProgressView.as_view(), name="company_progress_all"),
    path("company/kpi-dashboard/", KPIDashboardView.as_view(), name="company_kpi_dashboard"),
    # Employee Goals
    path("company/employees/<uuid:employee_id>/goals/", EmployeeGoalViewSet.as_view(), name="company_employee_goals"),
    path("company/goals/", EmployeeGoalViewSet.as_view(), name="company_goals_all"),
    path("company/goals/<uuid:goal_id>/", EmployeeGoalViewSet.as_view(), name="company_goal_detail"),
    path("", include(router.urls)),
]
