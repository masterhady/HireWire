
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.routers import DefaultRouter
from .supabase_test import test_supabase_connection
from .views import RegisterView, LoginView
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
    RAGSearchView,
    CVMatchView,
    CVUploadView,
    CVRecommendationsView,
    DashboardView,
    CareerAdvisorView,
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
)

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

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth_register"),
    path("auth/login/", LoginView.as_view(), name="auth_login"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("test-supabase/", test_supabase_connection, name="test_supabase_connection"),
    path("rag/search/", RAGSearchView.as_view(), name="rag_search"),
    path("rag/cv-match/", CVMatchView.as_view(), name="rag_cv_match"),
    path("rag/cv-upload/", CVUploadView.as_view(), name="rag_cv_upload"),
    path("rag/cv-recommendations/", CVRecommendationsView.as_view(), name="rag_cv_recommendations"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("career-advisor/", CareerAdvisorView.as_view(), name="career_advisor"),
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
    path("", include(router.urls)),
]
