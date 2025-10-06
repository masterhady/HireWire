from django.db import connection
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
import uuid

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
from .rag import embed_text, search_similar_jobs, generate_answer, chunk_text
from decouple import config

EMB_DIM = config("FIREWORKS_EMBEDDING_DIM", default=None, cast=int)


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
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["get"], url_path=r"by-company/(?P<company_id>\d+)")
    def by_company(self, request, company_id=None):
        queryset = self.get_queryset().filter(company_id=company_id)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        if response.status_code == status.HTTP_201_CREATED:
            job_id = response.data.get("id")
            title = response.data.get("title")
            description = response.data.get("description")
            requirements = response.data.get("requirements")
            text = f"{title}\n{description or ''}\n{requirements or ''}".strip()
            
            chunks = chunk_text(text)
            
            for i, chunk in enumerate(chunks or []):
                try:
                    emb = embed_text(chunk)
                    
                    if EMB_DIM and len(emb) != EMB_DIM:
                        continue
                        
                    with connection.cursor() as c:
                        c.execute(
                            "INSERT INTO job_embeddings (id, job_id, created_at, embedding) VALUES (%s, %s, NOW(), %s::vector)",
                            [str(uuid.uuid4()), str(job_id), emb],
                        )
                except Exception as e:
                    continue
        return response

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


class RAGSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        query = request.data.get("query")
        top_n = int(request.data.get("top_n", 5))
        similarity_threshold = float(request.data.get("similarity_threshold", 0.3))
        
        if not query:
            return Response({"detail": "query is required"}, status=400)
        
        try:
            q_emb = embed_text(query)
            rows = search_similar_jobs(q_emb, top_n=top_n, similarity_threshold=similarity_threshold)
            
            jobs = [
                {
                    "id": str(row[0]),
                    "title": row[1],
                    "description": row[2],
                    "requirements": row[3],
                    "company": str(row[4]),
                    "score": float(row[6]),
                }
                for row in rows
            ]
            
            summary = generate_answer(query, rows)
            
            return Response({
                "query": query, 
                "results": jobs, 
                "summary": summary,
                "total_matches": len(jobs),
                "similarity_threshold": similarity_threshold
            }, status=200)
            
        except Exception as e:
            return Response({"detail": str(e)}, status=400) 