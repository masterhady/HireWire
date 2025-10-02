
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
    path("", include(router.urls)),
]
