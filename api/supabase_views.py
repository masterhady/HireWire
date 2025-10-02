from django.db import connection
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .supabase_models import (
    SbCompany,
    SbUser,
    Skill,
    CV,
    CVEmbedding,
    Job,
    JobEmbedding,
    Application,
    Recommendation,
)
from .supabase_serializers import (
    CompanySerializer,
    SbUserSerializer,
    SkillSerializer,
    CVSerializer,
    CVEmbeddingSerializer,
    JobSerializer,
    JobEmbeddingSerializer,
    ApplicationSerializer,
    RecommendationSerializer,
)


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = SbCompany.objects.all()
    serializer_class = CompanySerializer
    permission_classes = [permissions.IsAuthenticated]


class SbUserViewSet(viewsets.ModelViewSet):
    queryset = SbUser.objects.all()
    serializer_class = SbUserSerializer
    permission_classes = [permissions.IsAuthenticated]


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class CVViewSet(viewsets.ModelViewSet):
    queryset = CV.objects.all()
    serializer_class = CVSerializer
    permission_classes = [permissions.IsAuthenticated]


class CVEmbeddingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CVEmbedding.objects.all()
    serializer_class = CVEmbeddingSerializer
    permission_classes = [permissions.IsAuthenticated]


class JobViewSet(viewsets.ModelViewSet):
    queryset = Job.objects.all()
    serializer_class = JobSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"], url_path="skills")
    def add_skill(self, request, pk=None):
        job_id = pk
        skill_id = request.data.get("skill_id")
        if not skill_id:
            return Response({"detail": "skill_id is required"}, status=400)
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO job_skills (job_id, skill_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    [job_id, skill_id],
                )
            except Exception as e:
                return Response({"detail": str(e)}, status=400)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["delete"], url_path="skills/(?P<skill_id>[0-9a-f\-]{36})")
    def remove_skill(self, request, pk=None, skill_id=None):
        job_id = pk
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM job_skills WHERE job_id = %s AND skill_id = %s",
                [job_id, skill_id],
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class JobEmbeddingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = JobEmbedding.objects.all()
    serializer_class = JobEmbeddingSerializer
    permission_classes = [permissions.IsAuthenticated]


class ApplicationViewSet(viewsets.ModelViewSet):
    queryset = Application.objects.all()
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.IsAuthenticated]


class RecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Recommendation.objects.all()
    serializer_class = RecommendationSerializer
    permission_classes = [permissions.IsAuthenticated] 