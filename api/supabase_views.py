from django.db import connection
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
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
    InterviewSession,
    InterviewQuestion,
    InterviewAnswer,
    InterviewEvaluation,
    AudioInterviewSession,
    AudioInterviewQuestion,
    AudioInterviewAnswer,
    AudioInterviewEvaluation,
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
    InterviewSessionSerializer,
    InterviewQuestionSerializer,
    InterviewAnswerSerializer,
    InterviewEvaluationSerializer,
    AudioInterviewSessionSerializer,
    AudioInterviewQuestionSerializer,
    AudioInterviewAnswerSerializer,
    AudioInterviewEvaluationSerializer,
)
from .rag import (
    embed_text,
    search_similar_jobs,
    generate_answer,
    chunk_text,
    FIREWORKS_BASE_URL,
    FIREWORKS_API_KEY,
)
from decouple import config
import re
import json
import requests
import os
import tempfile
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404

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
            title = response.data.get("title")
            description = response.data.get("description")
            requirements = response.data.get("requirements")
            text = (f"{title}\n{description or ''}\n{requirements or ''}").strip()
            
            chunks = chunk_text(text)
            
            embedding_errors = []
            for i, chunk in enumerate(chunks or []):
                try:
                    emb = embed_text(chunk)

                    if EMB_DIM and len(emb) != EMB_DIM:
                        embedding_errors.append(f"chunk_{i}: unexpected dim {len(emb)}")
                        continue

                    with connection.cursor() as c:
                        job_id = response.data.get("id")
                        emb_literal = "[" + ",".join(map(str, emb)) + "]"
                        c.execute(
                            "INSERT INTO job_embeddings (id, job_id, created_at, embedding) VALUES (%s, %s, NOW(), %s::vector)",
                            [str(uuid.uuid4()), str(job_id), emb_literal],
                        )
                except Exception as e:
                    # collect errors to return in the response for debugging
                    embedding_errors.append(f"chunk_{i}: {e}")

            # If there were embedding errors, attach them to the response for now
            if embedding_errors:
                # don't fail the creation; return a warning in the response body
                data = dict(response.data)
                data["embedding_warnings"] = embedding_errors
                return Response(data, status=response.status_code)
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
        must_contain = request.data.get("must_contain") or []
        must_not_contain = request.data.get("must_not_contain") or []
        
        if not query:
            return Response({"detail": "query is required"}, status=400)
        
        try:
            q_emb = embed_text(query)
            rows = search_similar_jobs(q_emb, top_n=top_n, similarity_threshold=similarity_threshold)
            
            jobs = []
            for row in rows or []:
                try:
                    if not row or len(row) < 6:
                        continue
                    # Handle two row shapes:
                    #  - With embedding: (.., embedding, score) → score at index 6
                    #  - Without embedding: (.., score) → score at index 5
                    score_idx = 6 if len(row) >= 7 else 5
                    score_val = row[score_idx]
                    if score_val is None:
                        continue
                    jobs.append({
                        "id": str(row[0]),
                        "title": row[1],
                        "description": row[2],
                        "requirements": row[3],
                        "company": str(row[4]) if row[4] is not None else None,
                        "score": float(score_val),
                    })
                except Exception:
                    # Skip malformed rows defensively
                    continue
            # Optional keyword filtering (case-insensitive)
            def _text_blob(j):
                return f"{j.get('title') or ''} {j.get('description') or ''} {j.get('requirements') or ''}".lower()

            if must_contain:
                kws = [str(k).lower() for k in (must_contain if isinstance(must_contain, list) else [must_contain])]
                jobs = [j for j in jobs if any(k in _text_blob(j) for k in kws)]

            if must_not_contain:
                bad = [str(k).lower() for k in (must_not_contain if isinstance(must_not_contain, list) else [must_not_contain])]
                jobs = [j for j in jobs if all(k not in _text_blob(j) for k in bad)]
            
            # If no rows were returned, try to sample a stored embedding to
            # detect a possible embedding-dimension mismatch (common cause when
            # embeddings were generated with a different dimension than the
            # current server config).
            stored_embedding_dim = None
            try:
                with connection.cursor() as c:
                    c.execute("SELECT embedding FROM job_embeddings LIMIT 1")
                    one = c.fetchone()
                    if one and one[0] is not None:
                        emb_val = one[0]
                        # pgvector may come back as a list, or a string like '[0.1,0.2,...]'
                        if isinstance(emb_val, (list, tuple)):
                            stored_embedding_dim = len(emb_val)
                        elif isinstance(emb_val, str):
                            s = emb_val.strip()
                            if s.startswith("[") and s.endswith("]"):
                                stored_embedding_dim = len([x for x in s[1:-1].split(",") if x.strip() != ""]) 
            except Exception:
                stored_embedding_dim = None

            summary = generate_answer(query, rows)

            # If no matches, include diagnostic info to help debug embedding
            # dimension mismatches or provider/config issues.
            if not jobs:
                return Response({
                    "query": query,
                    "results": jobs,
                    "summary": summary,
                    "total_matches": 0,
                    "similarity_threshold": similarity_threshold,
                    "diagnostic": {
                        "stored_embedding_dim": stored_embedding_dim,
                        "query_embedding_dim": len(q_emb) if isinstance(q_emb, (list, tuple)) else None,
                        "configured_fireworks_dim": EMB_DIM,
                    },
                }, status=200)

            return Response({
                "query": query, 
                "results": jobs, 
                "summary": summary,
                "total_matches": len(jobs),
                "similarity_threshold": similarity_threshold
            }, status=200)
            
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class CVMatchView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # New behavior: accept either cv_id (preferred) or raw cv_text. No file parsing here.
        # If neither is provided, use the most recently uploaded CV for the authenticated user.
        cv_id = request.data.get("cv_id")
        cv_text = request.data.get("cv_text")
        top_n = int(request.data.get("top_n", 5))
        similarity_threshold = float(request.data.get("similarity_threshold", 0.3))
        must_contain = request.data.get("must_contain") or []
        must_not_contain = request.data.get("must_not_contain") or []

        # If cv_id is provided, fetch parsed_text from DB
        if cv_id and not cv_text:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                return Response({"detail": "cv_id not found"}, status=404)

        # If neither cv_id nor cv_text provided, try to use last uploaded CV for authenticated user
        if not cv_id and not cv_text:
            try:
                auth_user = getattr(request, "user", None)
                auth_email = getattr(auth_user, "email", None)
                sb_user = None
                if auth_email:
                    sb_user = SbUser.objects.filter(email=auth_email).first()
                if not sb_user:
                    return Response({
                        "detail": "Associated Supabase user not found for authenticated account",
                        "hint": "Ensure a matching SbUser exists with the same email as the logged-in user",
                    }, status=404)
                latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
                if not latest_cv:
                    return Response({
                        "detail": "No uploaded CV found for the authenticated user",
                        "hint": "Upload a CV first using /api/rag/cv-upload/",
                    }, status=404)
                cv_text = latest_cv.parsed_text or ""
                if not cv_text:
                    return Response({
                        "detail": "Latest CV has no parsed_text",
                        "hint": "Re-upload the CV or provide cv_id/cv_text explicitly",
                    }, status=400)
            except Exception as e:
                return Response({"detail": str(e)}, status=400)

        if not cv_text:
            return Response({"detail": "cv_text or cv_id is required"}, status=400)

        try:
            # Embed the entire CV text. If very long, chunk first and average embeddings.
            chunks = chunk_text(cv_text)
            if not chunks:
                return Response({"detail": "No readable content in CV", "diagnostic": {"cv_text_len": len(cv_text or '')}}, status=400)

            emb_list = []
            for ch in chunks:
                try:
                    emb_list.append(embed_text(ch))
                except Exception:
                    continue

            if not emb_list:
                return Response({"detail": "Failed to embed CV content"}, status=400)

            # Search per chunk, aggregate by job with max score to avoid dilution
            job_id_to_best = {}
            for vec in emb_list:
                if not vec:
                    continue
                rows = search_similar_jobs(vec, top_n=max(top_n, 20), similarity_threshold=0.0)
                for row in rows or []:
                    try:
                        if not row or len(row) < 6:
                            continue
                        score_idx = 6 if len(row) >= 7 else 5
                        score_val = row[score_idx]
                        if score_val is None:
                            continue
                        job_id = str(row[0])
                        score_f = float(score_val)
                        existing = job_id_to_best.get(job_id)
                        if existing is None or score_f > existing.get("score", 0.0):
                            job_id_to_best[job_id] = {
                                "id": job_id,
                                "title": row[1],
                                "description": row[2],
                                "requirements": row[3],
                                "company": str(row[4]) if row[4] is not None else None,
                                "score": score_f,
                            }
                    except Exception:
                        continue

            # Build list and apply similarity_threshold
            jobs = [j for j in job_id_to_best.values() if j.get("score", 0.0) >= similarity_threshold]
            jobs.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            # Optional keyword filtering (case-insensitive)
            def _text_blob_cv(j):
                return f"{j.get('title') or ''} {j.get('description') or ''} {j.get('requirements') or ''}".lower()

            if must_contain:
                kws = [str(k).lower() for k in (must_contain if isinstance(must_contain, list) else [must_contain])]
                jobs = [j for j in jobs if any(k in _text_blob_cv(j) for k in kws)]

            if must_not_contain:
                bad = [str(k).lower() for k in (must_not_contain if isinstance(must_not_contain, list) else [must_not_contain])]
                jobs = [j for j in jobs if all(k not in _text_blob_cv(j) for k in bad)]

            if jobs:
                return Response({
                    "query_type": "cv",
                    "results": jobs,
                    "total_matches": len(jobs),
                    "similarity_threshold": similarity_threshold
                }, status=200)

            # If no matches, include diagnostics and a low-threshold sample to debug
            stored_embedding_dim = None
            total_embeddings = None
            active_embeddings = None
            try:
                with connection.cursor() as c:
                    c.execute("SELECT COUNT(*) FROM job_embeddings")
                    total_embeddings = c.fetchone()[0]
                    c.execute("SELECT embedding FROM job_embeddings LIMIT 1")
                    one = c.fetchone()
                    if one and one[0] is not None:
                        emb_val = one[0]
                        if isinstance(emb_val, (list, tuple)):
                            stored_embedding_dim = len(emb_val)
                        elif isinstance(emb_val, str):
                            s = emb_val.strip()
                            if s.startswith("[") and s.endswith("]"):
                                stored_embedding_dim = len([x for x in s[1:-1].split(",") if x.strip() != ""]) 
                    # Count active jobs that have embeddings
                    c.execute("""
                        SELECT COUNT(*)
                        FROM job_embeddings e
                        JOIN jobs j ON j.id = e.job_id
                        WHERE j.is_active = TRUE
                    """)
                    active_embeddings = c.fetchone()[0]
            except Exception:
                pass

            # Try again with a very low threshold to surface scores (using first chunk)
            sample_vec = emb_list[0]
            fallback_rows = search_similar_jobs(sample_vec, top_n=max(top_n, 10), similarity_threshold=0.0)
            fallback = []
            for row in fallback_rows or []:
                try:
                    if not row or len(row) < 7 or row[6] is None:
                        continue
                    fallback.append({
                        "id": str(row[0]),
                        "title": row[1],
                        "score": float(row[6]),
                    })
                except Exception:
                    continue

            # Extra diagnostics: check raw distances and query vector magnitude
            raw_dist_samples = []
            q_sum_abs = sum(abs(x) for x in sample_vec if isinstance(x, (int, float)))
            try:
                emb_literal = "[" + ",".join(map(str, sample_vec)) + "]"
                with connection.cursor() as c:
                    c.execute(
                        """
                        SELECT j.id,
                               (e.embedding <=> %s::vector) AS distance
                        FROM job_embeddings e
                        JOIN jobs j ON j.id = e.job_id
                        WHERE j.is_active = TRUE
                        ORDER BY distance NULLS LAST
                        LIMIT 5
                        """,
                        [emb_literal],
                    )
                    for rid, dist in c.fetchall() or []:
                        raw_dist_samples.append({"id": str(rid), "distance": None if dist is None else float(dist)})
            except Exception:
                pass

            return Response({
                "query_type": "cv",
                "results": jobs,
                "total_matches": 0,
                "similarity_threshold": similarity_threshold,
                "diagnostic": {
                    "stored_embedding_dim": stored_embedding_dim,
                    "query_embedding_dim": len(sample_vec) if sample_vec else None,
                    "configured_fireworks_dim": EMB_DIM,
                    "total_embeddings": total_embeddings,
                    "active_embeddings": active_embeddings,
                    "low_threshold_samples": fallback[:5],
                    "query_vector_sum_abs": q_sum_abs,
                    "raw_distance_samples": raw_dist_samples,
                },
            }, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class CVUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Upload and parse a CV (file or cv_text), store in DB, return cv_id.

        Body (multipart/form-data or JSON):
          - user: UUID (required)
          - file: .txt/.pdf/.docx OR cv_text (string)
          - filename: optional when using cv_text
        """
        filename = request.data.get("filename") or "uploaded_cv.txt"
        cv_text = request.data.get("cv_text")

        # Support file upload: .txt, .pdf, .docx
        if not cv_text and hasattr(request, 'FILES'):
            f = request.FILES.get('file') or request.FILES.get('cv_file')
            if f is not None:
                try:
                    name = getattr(f, 'name', '') or ''
                    if not request.data.get("filename"):
                        filename = name or filename
                    lower_name = name.lower()
                    content_type = getattr(f, 'content_type', '') or ''
                    content = f.read()
                    if lower_name.endswith('.txt') or content_type.startswith('text/'):
                        try:
                            cv_text = content.decode('utf-8')
                        except Exception:
                            cv_text = content.decode('latin-1', errors='ignore')
                    elif lower_name.endswith('.pdf') or 'pdf' in content_type:
                        try:
                            import PyPDF2  # type: ignore
                            from io import BytesIO
                            pdf = PyPDF2.PdfReader(BytesIO(content))
                            parts = []
                            for page in pdf.pages:
                                try:
                                    parts.append(page.extract_text() or '')
                                except Exception:
                                    continue
                            cv_text = "\n".join(parts).strip()
                        except Exception as e:
                            return Response({
                                "detail": f"PDF parsing failed: {e}",
                                "hint": "Install PyPDF2 or upload a .txt file",
                            }, status=400)
                    elif lower_name.endswith('.docx') or 'officedocument.wordprocessingml' in content_type:
                        try:
                            import docx  # type: ignore
                            from io import BytesIO
                            doc = docx.Document(BytesIO(content))
                            cv_text = "\n".join(p.text for p in doc.paragraphs).strip()
                        except Exception as e:
                            return Response({
                                "detail": f"DOCX parsing failed: {e}",
                                "hint": "Install python-docx or upload a .txt file",
                            }, status=400)
                    else:
                        return Response({
                            "detail": "Unsupported file type for CV",
                            "hint": "Upload .txt, .pdf, or .docx",
                            "received_content_type": content_type,
                            "filename": name,
                        }, status=400)
                except Exception as e:
                    return Response({"detail": f"Could not read uploaded file: {e}"}, status=400)

        # Basic validation: ensure provided content resembles a CV
        def _looks_like_cv(txt: str) -> bool:
            try:
                s = (txt or "").strip()
                if len(s) < 300:
                    return False
                low = s.lower()
                section_hits = 0
                for kw in ["experience", "education", "skills", "projects", "summary", "work", "career"]:
                    if kw in low:
                        section_hits += 1
                has_email = bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", s))
                has_phone = bool(re.search(r"\+?\d[\d\s().-]{7,}", s))
                return section_hits >= 2 and (has_email or has_phone)
            except Exception:
                return False

        # Resolve SbUser (supabase) from authenticated Django user via email
        sb_user = None
        try:
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
        except Exception:
            sb_user = None

        if not sb_user:
            return Response({
                "detail": "Associated Supabase user not found for authenticated account",
                "hint": "Ensure a matching SbUser exists with the same email as the logged-in user",
            }, status=404)
        if not cv_text:
            return Response({"detail": "cv_text or file is required"}, status=400)
        if not _looks_like_cv(cv_text):
            return Response({
                "detail": "Uploaded content does not appear to be a CV",
                "hint": "Ensure the file contains resume sections like Experience, Education, Skills and contact info",
            }, status=415)

        try:
            # Upsert single CV per user: update if exists, else create
            existing_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
            embedding_warnings = []
            if existing_cv:
                existing_cv.filename = filename
                existing_cv.parsed_text = cv_text
                existing_cv.updated_at = timezone.now()
                existing_cv.save(update_fields=["filename", "parsed_text", "updated_at"])
                # Remove old embeddings for this CV
                try:
                    with connection.cursor() as c:
                        c.execute("DELETE FROM cv_embeddings WHERE cv_id = %s", [str(existing_cv.id)])
                except Exception as e:
                    embedding_warnings.append(f"cleanup: {e}")
                target_cv = existing_cv
                status_code = 200
            else:
                target_cv = CV.objects.create(
                    user_id=sb_user.id,
                    filename=filename,
                    parsed_text=cv_text,
                    created_at=timezone.now(),
                    updated_at=timezone.now(),
                )
                status_code = 201

            # Create embeddings for CV text (chunked)
            chunks = chunk_text(cv_text)
            for i, chunk in enumerate(chunks or []):
                try:
                    emb = embed_text(chunk)
                    if EMB_DIM and len(emb) != EMB_DIM:
                        embedding_warnings.append(f"chunk_{i}: unexpected dim {len(emb)}")
                        continue
                    with connection.cursor() as c:
                        emb_literal = "[" + ",".join(map(str, emb)) + "]"
                        c.execute(
                            "INSERT INTO cv_embeddings (id, cv_id, created_at, embedding) VALUES (%s, %s, NOW(), %s::vector)",
                            [str(uuid.uuid4()), str(target_cv.id), emb_literal],
                        )
                except Exception as e:
                    embedding_warnings.append(f"chunk_{i}: {e}")

            resp = {
                "id": str(target_cv.id),
                "user": str(target_cv.user_id),
                "filename": target_cv.filename,
                "parsed_text_len": len(target_cv.parsed_text or ''),
            }
            if embedding_warnings:
                resp["embedding_warnings"] = embedding_warnings
            return Response(resp, status=status_code)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class CVRecommendationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Generate recommendation metrics and suggestions for a CV.

        Accepts one of:
          - cv_id: use a stored CV
          - cv_text: raw CV text
          - none: use the latest CV of the authenticated user
        """
        cv_id = request.data.get("cv_id")
        cv_text = request.data.get("cv_text")

        # Resolve CV text
        if cv_id and not cv_text:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                return Response({"detail": "cv_id not found"}, status=404)

        if not cv_id and not cv_text:
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            sb_user = None
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
            if not sb_user:
                return Response({
                    "detail": "Associated Supabase user not found for authenticated account",
                    "hint": "Ensure a matching SbUser exists with the same email as the logged-in user",
                }, status=404)
            latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
            if not latest_cv:
                return Response({
                    "detail": "No uploaded CV found for the authenticated user",
                    "hint": "Upload a CV first using /api/rag/cv-upload/",
                }, status=404)
            cv_text = latest_cv.parsed_text or ""

        if not cv_text:
            return Response({"detail": "cv_text is empty"}, status=400)

        text = cv_text.strip()

        # Call Fireworks chat model to analyze and return structured JSON
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        system_prompt = (
            "You are an expert ATS resume analyzer. "
            "Given the raw CV text, analyze it and return STRICT JSON (no prose). "
            "Return fields: overall_score (0-100), skills_match (0-100), experience_relevance (0-100), ats_readability (0-100), "
            "suggestions (array of objects: {title, priority in [high, medium, low], details}), and cv_extract. "
            "cv_extract must summarize the CV for UI display with: full_name, job_title, summary, skills (array of strings), "
            "experience (array of {company, role, period, bullets[array of strings]}), and contact {email, phone}. "
            "Tailor suggestions and cv_extract to the provided CV content; do NOT output placeholders or generic text. "
            "Base everything solely on the provided CV."
        )
        user_prompt = (
            "CV Text:\n" + text + "\n\n"+
            "Output a single JSON object with the exact keys described."
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return Response({"detail": f"Model call failed: {e}"}, status=400)

        def _parse_json(s: str):
            try:
                return json.loads(s)
            except Exception:
                # Attempt to extract the first JSON object
                m = re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except Exception:
                        return None
                return None

        data = _parse_json(content)
        if not isinstance(data, dict):
            return Response({
                "detail": "Model returned non-JSON output",
                "raw": content,
            }, status=400)

        # Coerce and clamp fields defensively
        def _clamp_int(v, lo=0, hi=100):
            try:
                return max(lo, min(hi, int(round(float(v)))))
            except Exception:
                return 0

        cv_extract = data.get("cv_extract") or {}
        # Normalize cv_extract fields defensively
        if not isinstance(cv_extract, dict):
            cv_extract = {}
        result = {
            "overall_score": _clamp_int(data.get("overall_score")),
            "skills_match": _clamp_int(data.get("skills_match")),
            "experience_relevance": _clamp_int(data.get("experience_relevance")),
            "ats_readability": _clamp_int(data.get("ats_readability")),
            "suggestions": data.get("suggestions") or [],
            "cv_extract": {
                "full_name": cv_extract.get("full_name"),
                "job_title": cv_extract.get("job_title"),
                "summary": cv_extract.get("summary"),
                "skills": cv_extract.get("skills") or [],
                "experience": cv_extract.get("experience") or [],
                "contact": cv_extract.get("contact") or {},
            },
            "analyzed_chars": len(text),
        }
        return Response(result, status=200)


class DashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            # Resolve authenticated supabase user
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            sb_user = None
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
            if not sb_user:
                return Response({
                    "detail": "Associated Supabase user not found for authenticated account",
                    "hint": "Ensure a matching SbUser exists with the same email as the logged-in user",
                }, status=404)

            latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
            cv_text = (latest_cv.parsed_text if latest_cv else None) or ""

            # Compute top matches using the CV (if present)
            top_matches = []
            total_matches = 0
            if cv_text:
                chunks = chunk_text(cv_text)
                emb_list = []
                for ch in chunks:
                    try:
                        emb_list.append(embed_text(ch))
                    except Exception:
                        continue
                # Aggregate by job with best score across chunks
                job_id_to_best = {}
                for vec in emb_list:
                    if not vec:
                        continue
                    rows = search_similar_jobs(vec, top_n=50, similarity_threshold=0.0)
                    for row in rows or []:
                        try:
                            if not row or len(row) < 6:
                                continue
                            score_idx = 6 if len(row) >= 7 else 5
                            score_val = row[score_idx]
                            if score_val is None:
                                continue
                            job_id = str(row[0])
                            score_f = float(score_val)
                            existing = job_id_to_best.get(job_id)
                            if existing is None or score_f > existing.get("score", 0.0):
                                job_obj = {
                                    "id": job_id,
                                    "title": row[1],
                                    "description": row[2],
                                    "requirements": row[3],
                                    "company": str(row[4]) if row[4] is not None else None,
                                    "score": score_f,
                                }
                                job_id_to_best[job_id] = job_obj
                        except Exception:
                            continue
                matches = list(job_id_to_best.values())
                matches.sort(key=lambda x: x.get("score", 0.0), reverse=True)
                total_matches = len(matches)
                top_matches = [{
                    "id": m.get("id"),
                    "title": m.get("title"),
                    "company": m.get("company"),
                    "score": round(float(m.get("score", 0.0)) * 100),
                } for m in matches[:3]]

            # Get AI-driven CV score via Fireworks (reuse the same model setup)
            cv_score_value = None
            if cv_text:
                system_prompt = (
                    "You are an expert ATS resume analyzer. Return STRICT JSON with one key: overall_score (0-100)."
                )
                user_prompt = "CV Text:\n" + cv_text + "\n\nOutput: {\"overall_score\": 87}"
                if not FIREWORKS_API_KEY:
                    cv_score_value = None
                else:
                    try:
                        url = f"{FIREWORKS_BASE_URL}/chat/completions"
                        model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
                        headers = {
                            "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                            "Content-Type": "application/json",
                        }
                        payload = {
                            "model": model_name,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"},
                        }
                        r = requests.post(url, headers=headers, json=payload, timeout=45)
                        if r.ok:
                            data_resp = r.json()
                            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "")
                            try:
                                obj = json.loads(content)
                                v = obj.get("overall_score")
                                if isinstance(v, (int, float)):
                                    cv_score_value = int(round(float(v)))
                            except Exception:
                                cv_score_value = None
                    except Exception:
                        cv_score_value = None

            resp = {
                "job_matches": {"count": total_matches},
                "cv_score": {"value": cv_score_value},
                "profile_views": {"value": 0},
                "top_matches": top_matches,
            }
            return Response(resp, status=200)
        except Exception as e:
            return Response({"detail": str(e)}, status=400)


class CareerAdvisorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """AI Career Advisor: Analyze CV and provide career path guidance.

        Accepts one of:
          - cv_id: use a stored CV
          - cv_text: raw CV text
          - none: use the latest CV of the authenticated user
        """
        cv_id = request.data.get("cv_id")
        cv_text = request.data.get("cv_text")

        # Resolve CV text (same logic as recommendations)
        if cv_id and not cv_text:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                return Response({"detail": "cv_id not found"}, status=404)

        if not cv_id and not cv_text:
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            sb_user = None
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
            if not sb_user:
                return Response({
                    "detail": "Associated Supabase user not found for authenticated account",
                    "hint": "Ensure a matching SbUser exists with the same email as the logged-in user",
                }, status=404)
            latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
            if not latest_cv:
                return Response({
                    "detail": "No uploaded CV found for the authenticated user",
                    "hint": "Upload a CV first using /api/rag/cv-upload/",
                }, status=404)
            cv_text = latest_cv.parsed_text or ""

        if not cv_text:
            return Response({"detail": "cv_text is empty"}, status=400)

        text = cv_text.strip()

        # Call Fireworks for career guidance
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        system_prompt = (
            "You are an expert career advisor and talent acquisition specialist. "
            "Analyze the provided CV and return STRICT JSON with career guidance. "
            "Return fields: current_role_assessment, career_paths (array of objects with title, description, transition_difficulty, growth_potential), "
            "skills_gaps (array of strings), market_demand (array of objects with role, demand_level, salary_range), "
            "recommendations (array of strings), and next_steps (array of strings). "
            "Base all advice on the actual CV content; be specific and actionable."
        )
        user_prompt = (
            "CV Text:\n" + text + "\n\n" +
            "Provide career guidance in this JSON format:\n" +
            '{"current_role_assessment": "Brief assessment of current position", '
            '"career_paths": [{"title": "Data Scientist", "description": "Transition to advanced analytics", "transition_difficulty": "medium", "growth_potential": "high"}], '
            '"skills_gaps": ["Python", "Machine Learning"], '
            '"market_demand": [{"role": "Data Analyst", "demand_level": "high", "salary_range": "$60k-90k"}], '
            '"recommendations": ["Learn Python programming", "Get certified in data analysis"], '
            '"next_steps": ["Update LinkedIn profile", "Apply to 5 data analyst positions"]}'
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return Response({"detail": f"Model call failed: {e}"}, status=400)

        def _parse_json(s: str):
            try:
                return json.loads(s)
            except Exception:
                m = re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except Exception:
                        return None
                return None

        data = _parse_json(content)
        if not isinstance(data, dict):
            return Response({
                "detail": "Model returned non-JSON output",
                "raw": content,
            }, status=400)

        # Normalize response defensively
        result = {
            "current_role_assessment": data.get("current_role_assessment", ""),
            "career_paths": data.get("career_paths") or [],
            "skills_gaps": data.get("skills_gaps") or [],
            "market_demand": data.get("market_demand") or [],
            "recommendations": data.get("recommendations") or [],
            "next_steps": data.get("next_steps") or [],
            "analyzed_chars": len(text),
        }
        return Response(result, status=200)


class InterviewQuestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Generate AI-powered interview questions based on CV and target job.

        Body:
          - cv_id (optional): use stored CV
          - cv_text (optional): raw CV text
          - job_description (required): target job description
          - question_count (optional): number of questions (default 10)
          - difficulty (optional): easy/medium/hard (default medium)
        """
        cv_id = request.data.get("cv_id")
        cv_text = request.data.get("cv_text")
        job_description = request.data.get("job_description")
        question_count = int(request.data.get("question_count", 10))
        difficulty = request.data.get("difficulty", "medium")

        if not job_description:
            return Response({"detail": "job_description is required"}, status=400)

        # Resolve CV text (same logic as other endpoints)
        if cv_id and not cv_text:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                return Response({"detail": "cv_id not found"}, status=404)

        if not cv_id and not cv_text:
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            sb_user = None
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
            if not sb_user:
                return Response({
                    "detail": "Associated Supabase user not found for authenticated account",
                    "hint": "Ensure a matching SbUser exists with the same email as the logged-in user",
                }, status=404)
            latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
            if not latest_cv:
                return Response({
                    "detail": "No uploaded CV found for the authenticated user",
                    "hint": "Upload a CV first using /api/rag/cv-upload/",
                }, status=404)
            cv_text = latest_cv.parsed_text or ""

        if not cv_text:
            return Response({"detail": "cv_text is empty"}, status=400)

        # Call Fireworks for interview questions
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        system_prompt = (
            "You are an expert interview coach and hiring manager. "
            "Generate personalized interview questions based on the candidate's CV and target job description. "
            "Return STRICT JSON with questions array. Each question should have: question, category, difficulty, tips, and expected_answer_focus. "
            "Base questions on the actual CV content and job requirements; make them specific and relevant."
        )
        user_prompt = (
            f"Candidate CV:\n{cv_text}\n\n"
            f"Target Job Description:\n{job_description}\n\n"
            f"Generate {question_count} {difficulty} difficulty interview questions in this JSON format:\n"
            '{"questions": [{"question": "Tell me about a challenging project you worked on", "category": "behavioral", "difficulty": "medium", "tips": "Use STAR method", "expected_answer_focus": "problem-solving and leadership"}]}'
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return Response({"detail": f"Model call failed: {e}"}, status=400)

        def _parse_json(s: str):
            try:
                return json.loads(s)
            except Exception:
                m = re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except Exception:
                        return None
                return None

        data = _parse_json(content)
        if not isinstance(data, dict):
            return Response({
                "detail": "Model returned non-JSON output",
                "raw": content,
            }, status=400)

        # Store interview session and questions
        try:
            # Create interview session
            session = InterviewSession.objects.create(
                user_id=sb_user.id,
                job_description=job_description,
                difficulty=difficulty,
                created_at=timezone.now(),
            )
            
            # Store each question
            stored_questions = []
            for q in data.get("questions") or []:
                question_obj = InterviewQuestion.objects.create(
                    session_id=session.id,
                    question=q.get("question", ""),
                    category=q.get("category", ""),
                    difficulty=q.get("difficulty", difficulty),
                    tips=q.get("tips", ""),
                    expected_answer_focus=q.get("expected_answer_focus", ""),
                    created_at=timezone.now(),
                )
                stored_questions.append({
                    "id": str(question_obj.id),
                    "question": question_obj.question,
                    "category": question_obj.category,
                    "difficulty": question_obj.difficulty,
                    "tips": question_obj.tips,
                    "expected_answer_focus": question_obj.expected_answer_focus,
                })
            
            result = {
                "session_id": str(session.id),
                "questions": stored_questions,
                "job_description": job_description,
                "difficulty": difficulty,
                "question_count": len(stored_questions),
                "instructions": "Answer all questions, then use /api/interview/submit-all-answers/ to submit all answers for batch evaluation.",
                "flow": "batch_processing"
            }
            return Response(result, status=200)
            
        except Exception as e:
            return Response({"detail": f"Failed to store interview session: {str(e)}"}, status=400)


class InterviewPracticeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Chat-style interview practice with AI interviewer.

        Body:
          - question (required): the interview question
          - answer (required): candidate's answer
          - cv_id (optional): for context
          - cv_text (optional): for context
          - job_description (optional): for context
        """
        question = request.data.get("question")
        answer = request.data.get("answer")
        cv_id = request.data.get("cv_id")
        cv_text = request.data.get("cv_text")
        job_description = request.data.get("job_description", "")

        if not question or not answer:
            return Response({"detail": "question and answer are required"}, status=400)

        # Resolve CV text for context
        if cv_id and not cv_text:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                cv_text = ""

        if not cv_id and not cv_text:
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            sb_user = None
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
            if sb_user:
                latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
                if latest_cv:
                    cv_text = latest_cv.parsed_text or ""

        # Call Fireworks for interview feedback
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        system_prompt = (
            "You are an expert interview coach providing constructive feedback. "
            "Analyze the candidate's answer and return STRICT JSON with: "
            "overall_score (0-100), strengths (array), areas_for_improvement (array), "
            "follow_up_question (string), and detailed_feedback (string). "
            "Be encouraging but honest in your assessment."
        )
        
        context_parts = []
        if cv_text:
            context_parts.append(f"Candidate Background:\n{cv_text}")
        if job_description:
            context_parts.append(f"Job Context:\n{job_description}")
        context = "\n\n".join(context_parts)

        user_prompt = (
            f"{context}\n\n"
            f"Interview Question: {question}\n\n"
            f"Candidate's Answer: {answer}\n\n"
            "Provide feedback in this JSON format:\n"
            '{"overall_score": 75, "strengths": ["Good use of examples", "Clear communication"], '
            '"areas_for_improvement": ["Could be more specific", "Missing quantifiable results"], '
            '"follow_up_question": "Can you elaborate on the specific challenges you faced?", '
            '"detailed_feedback": "Your answer shows good understanding but could benefit from more specific details..."}'
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return Response({"detail": f"Model call failed: {e}"}, status=400)

        def _parse_json(s: str):
            try:
                return json.loads(s)
            except Exception:
                m = re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except Exception:
                        return None
                return None

        data = _parse_json(content)
        if not isinstance(data, dict):
            return Response({
                "detail": "Model returned non-JSON output",
                "raw": content,
            }, status=400)

        # Normalize response defensively
        def _clamp_score(v):
            try:
                return max(0, min(100, int(round(float(v)))))
            except Exception:
                return 0

        result = {
            "overall_score": _clamp_score(data.get("overall_score", 0)),
            "strengths": data.get("strengths") or [],
            "areas_for_improvement": data.get("areas_for_improvement") or [],
            "follow_up_question": data.get("follow_up_question", ""),
            "detailed_feedback": data.get("detailed_feedback", ""),
            "question": question,
            "answer": answer,
        }
        return Response(result, status=200)


class InterviewAnswerEvaluationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Evaluate user's answer to interview question and provide correct answer.

        Body:
          - question (required): the interview question
          - user_answer (required): user's answer
          - cv_id (optional): for context
          - cv_text (optional): for context
          - job_description (optional): for context
        """
        question = request.data.get("question")
        user_answer = request.data.get("user_answer")
        cv_id = request.data.get("cv_id")
        cv_text = request.data.get("cv_text")
        job_description = request.data.get("job_description", "")

        if not question or not user_answer:
            return Response({"detail": "question and user_answer are required"}, status=400)

        # Resolve CV text for context
        if cv_id and not cv_text:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                cv_text = ""

        if not cv_id and not cv_text:
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            sb_user = None
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
            if sb_user:
                latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
                if latest_cv:
                    cv_text = latest_cv.parsed_text or ""

        # Call Fireworks for answer evaluation and correct answer
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        system_prompt = (
            "You are an expert interview coach and hiring manager. "
            "Evaluate the candidate's answer and provide the correct/ideal answer. "
            "Return STRICT JSON with: "
            "overall_score (0-100), strengths (array), weaknesses (array), "
            "correct_answer (string), answer_analysis (string), "
            "improvement_tips (array), and follow_up_questions (array). "
            "Be constructive and educational in your feedback."
        )
        
        context_parts = []
        if cv_text:
            context_parts.append(f"Candidate Background:\n{cv_text}")
        if job_description:
            context_parts.append(f"Job Context:\n{job_description}")
        context = "\n\n".join(context_parts)

        user_prompt = (
            f"{context}\n\n"
            f"Interview Question: {question}\n\n"
            f"Candidate's Answer: {user_answer}\n\n"
            "Evaluate the answer and provide feedback in this JSON format:\n"
            '{"overall_score": 75, "strengths": ["Good technical knowledge", "Clear communication"], '
            '"weaknesses": ["Missing specific examples", "Could be more detailed"], '
            '"correct_answer": "The ideal answer would include...", '
            '"answer_analysis": "Your answer shows understanding but...", '
            '"improvement_tips": ["Use STAR method", "Include specific metrics"], '
            '"follow_up_questions": ["Can you elaborate on...", "What challenges did you face?"]}'
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return Response({"detail": f"Model call failed: {e}"}, status=400)

        def _parse_json(s: str):
            try:
                return json.loads(s)
            except Exception:
                m = re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except Exception:
                        return None
                return None

        data = _parse_json(content)
        if not isinstance(data, dict):
            return Response({
                "detail": "Model returned non-JSON output",
                "raw": content,
            }, status=400)

        # Normalize response defensively
        def _clamp_score(v):
            try:
                return max(0, min(100, int(round(float(v)))))
            except Exception:
                return 0

        # Store evaluation results
        try:
            # Get the answer record (assuming answer_id is provided)
            answer_id = request.data.get("answer_id")
            if answer_id:
                try:
                    answer = InterviewAnswer.objects.get(id=answer_id)
                except InterviewAnswer.DoesNotExist:
                    return Response({"detail": "Answer not found"}, status=404)
            else:
                # Create answer record if not provided
                answer = InterviewAnswer.objects.create(
                    question_id=None,  # Will be set if question_id is provided
                    user_answer=user_answer,
                    submitted_at=timezone.now(),
                )
            
            # Store evaluation
            evaluation = InterviewEvaluation.objects.create(
                answer_id=answer.id,
                overall_score=_clamp_score(data.get("overall_score", 0)),
                strengths=data.get("strengths") or [],
                weaknesses=data.get("weaknesses") or [],
                correct_answer=data.get("correct_answer", ""),
                answer_analysis=data.get("answer_analysis", ""),
                improvement_tips=data.get("improvement_tips") or [],
                follow_up_questions=data.get("follow_up_questions") or [],
                evaluated_at=timezone.now(),
            )
            
            result = {
                "evaluation_id": str(evaluation.id),
                "overall_score": evaluation.overall_score,
                "strengths": evaluation.strengths,
                "weaknesses": evaluation.weaknesses,
                "correct_answer": evaluation.correct_answer,
                "answer_analysis": evaluation.answer_analysis,
                "improvement_tips": evaluation.improvement_tips,
                "follow_up_questions": evaluation.follow_up_questions,
                "question": question,
                "user_answer": user_answer,
            }
            return Response(result, status=200)
            
        except Exception as e:
            return Response({"detail": f"Failed to store evaluation: {str(e)}"}, status=400)


class InterviewAnswerSubmissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Submit user's answer to an interview question.

        Body:
          - question_id (required): UUID of the interview question
          - user_answer (required): user's answer text
        """
        question_id = request.data.get("question_id")
        user_answer = request.data.get("user_answer")

        if not question_id or not user_answer:
            return Response({"detail": "question_id and user_answer are required"}, status=400)

        try:
            # Verify question exists
            question = InterviewQuestion.objects.get(id=question_id)
            
            # Store the answer
            answer = InterviewAnswer.objects.create(
                question_id=question_id,
                user_answer=user_answer,
                submitted_at=timezone.now(),
            )
            
            return Response({
                "answer_id": str(answer.id),
                "question_id": str(question_id),
                "user_answer": user_answer,
                "submitted_at": answer.submitted_at,
            }, status=201)
            
        except InterviewQuestion.DoesNotExist:
            return Response({"detail": "Question not found"}, status=404)
        except Exception as e:
            return Response({"detail": f"Failed to store answer: {str(e)}"}, status=400)


class InterviewBatchSubmissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Submit all answers for a session and get batch AI evaluation.

        Body:
          - session_id (required): interview session ID
          - answers (required): array of {question_id, user_answer}
        """
        session_id = request.data.get("session_id")
        answers_data = request.data.get("answers", [])

        if not session_id:
            return Response({"detail": "session_id is required"}, status=400)
        
        if not answers_data or not isinstance(answers_data, list):
            return Response({"detail": "answers array is required"}, status=400)

        try:
            # Verify user owns this session
            sb_user = SbUser.objects.get(email=request.user.email)
            session = InterviewSession.objects.get(id=session_id, user_id=sb_user.id)
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        except InterviewSession.DoesNotExist:
            return Response({"detail": "Session not found or access denied"}, status=404)

        # Get all questions for this session
        questions = InterviewQuestion.objects.filter(session_id=session_id)
        question_dict = {str(q.id): q for q in questions}

        # Validate and store all answers
        stored_answers = []
        for answer_data in answers_data:
            question_id = answer_data.get("question_id")
            user_answer = answer_data.get("user_answer", "").strip()
            
            if not question_id or not user_answer:
                continue
                
            if question_id not in question_dict:
                continue
                
            try:
                # Check if answer already exists, update or create
                answer, created = InterviewAnswer.objects.get_or_create(
                    question_id=question_id,
                    defaults={
                        'user_answer': user_answer,
                        'submitted_at': timezone.now(),
                    }
                )
                if not created:
                    answer.user_answer = user_answer
                    answer.submitted_at = timezone.now()
                    answer.save()
                
                stored_answers.append({
                    'answer_id': str(answer.id),
                    'question_id': question_id,
                    'question': question_dict[question_id].question,
                    'user_answer': user_answer,
                    'answer_obj': answer
                })
            except Exception as e:
                continue

        if not stored_answers:
            return Response({"detail": "No valid answers to process"}, status=400)

        # Get CV context for evaluation
        cv_text = ""
        latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
        if latest_cv:
            cv_text = latest_cv.parsed_text or ""

        # Call Fireworks for batch evaluation
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        # Prepare batch evaluation prompt
        system_prompt = (
            "You are an expert interview coach providing comprehensive feedback on a complete interview session. "
            "Analyze all questions and answers together to provide holistic evaluation. "
            "Return STRICT JSON with evaluations array. Each evaluation should have: "
            "overall_score (0-100), strengths (array), weaknesses (array), "
            "correct_answer (string), answer_analysis (string), improvement_tips (array), "
            "follow_up_questions (array). "
            "Consider the flow and consistency across all answers."
        )

        # Build context for all Q&A pairs
        qa_context = []
        for i, answer_data in enumerate(stored_answers, 1):
            qa_context.append(
                f"Question {i}: {answer_data['question']}\n"
                f"Candidate's Answer {i}: {answer_data['user_answer']}"
            )

        user_prompt = (
            f"Candidate Background:\n{cv_text}\n\n"
            f"Job Description:\n{session.job_description}\n\n"
            f"Interview Session (Complete):\n" + "\n\n".join(qa_context) + "\n\n"
            "Provide comprehensive evaluation for each answer in this JSON format:\n"
            '{"evaluations": [{"overall_score": 85, "strengths": ["Clear examples", "Good structure"], '
            '"weaknesses": ["Could be more specific", "Missing metrics"], '
            '"correct_answer": "The ideal answer would include...", '
            '"answer_analysis": "Your response demonstrates...", '
            '"improvement_tips": ["Add specific metrics", "Include more details"], '
            '"follow_up_questions": ["Can you elaborate on...", "What was the impact of..."]}]}'
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=120)  # Longer timeout for batch
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            def _parse_json(s: str):
                try:
                    return json.loads(s)
                except Exception:
                    m = re.search(r"\{[\s\S]*\}", s)
                    if m:
                        try:
                            return json.loads(m.group(0))
                        except Exception:
                            return None
                    return None

            evaluation_data = _parse_json(content)
            if not isinstance(evaluation_data, dict) or "evaluations" not in evaluation_data:
                return Response({
                    "detail": "Model returned invalid evaluation format",
                    "raw": content,
                }, status=400)

            evaluations = evaluation_data.get("evaluations", [])
            
            # Store evaluations in database
            stored_evaluations = []
            for i, eval_data in enumerate(evaluations):
                if i >= len(stored_answers):
                    break
                    
                answer_obj = stored_answers[i]['answer_obj']
                
                # Delete existing evaluation if any
                InterviewEvaluation.objects.filter(answer_id=answer_obj.id).delete()
                
                # Create new evaluation
                evaluation = InterviewEvaluation.objects.create(
                    answer_id=answer_obj.id,
                    overall_score=eval_data.get("overall_score", 0),
                    strengths=eval_data.get("strengths", []),
                    weaknesses=eval_data.get("weaknesses", []),
                    correct_answer=eval_data.get("correct_answer", ""),
                    answer_analysis=eval_data.get("answer_analysis", ""),
                    improvement_tips=eval_data.get("improvement_tips", []),
                    follow_up_questions=eval_data.get("follow_up_questions", []),
                    evaluated_at=timezone.now(),
                )
                
                stored_evaluations.append({
                    "evaluation_id": str(evaluation.id),
                    "answer_id": str(answer_obj.id),
                    "question_id": stored_answers[i]['question_id'],
                    "question": stored_answers[i]['question'],
                    "user_answer": stored_answers[i]['user_answer'],
                    "evaluation": InterviewEvaluationSerializer(evaluation).data
                })

            # Calculate session statistics
            scores = [eval_data.get("overall_score", 0) for eval_data in evaluations if eval_data.get("overall_score")]
            average_score = sum(scores) / len(scores) if scores else 0
            
            return Response({
                "session_id": str(session_id),
                "total_questions": len(stored_answers),
                "total_evaluations": len(stored_evaluations),
                "average_score": round(average_score, 1),
                "evaluations": stored_evaluations,
                "session_complete": True,
                "message": "All answers evaluated successfully using batch AI processing"
            }, status=200)

        except Exception as e:
            return Response({"detail": f"Batch evaluation failed: {str(e)}"}, status=400)


class InterviewHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's interview history and progress.

        Query params:
          - limit (optional): number of sessions to return (default: 10)
          - session_id (optional): get specific session details
        """
        try:
            sb_user = SbUser.objects.get(email=request.user.email)
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        limit = int(request.query_params.get("limit", 10))
        session_id = request.query_params.get("session_id")

        if session_id:
            # Get specific session with all details
            try:
                session = InterviewSession.objects.get(id=session_id, user_id=sb_user.id)
                questions = InterviewQuestion.objects.filter(session_id=session.id)
                
                session_data = {
                    "session": InterviewSessionSerializer(session).data,
                    "questions": []
                }
                
                for question in questions:
                    question_data = InterviewQuestionSerializer(question).data
                    
                    # Get answers and evaluations for this question
                    answers = InterviewAnswer.objects.filter(question_id=question.id)
                    question_data["answers"] = []
                    
                    for answer in answers:
                        answer_data = InterviewAnswerSerializer(answer).data
                        
                        # Get evaluation for this answer
                        try:
                            evaluation = InterviewEvaluation.objects.get(answer_id=answer.id)
                            answer_data["evaluation"] = InterviewEvaluationSerializer(evaluation).data
                        except InterviewEvaluation.DoesNotExist:
                            answer_data["evaluation"] = None
                        
                        question_data["answers"].append(answer_data)
                    
                    session_data["questions"].append(question_data)
                
                return Response(session_data, status=200)
                
            except InterviewSession.DoesNotExist:
                return Response({"detail": "Session not found"}, status=404)
        else:
            # Get recent sessions summary
            sessions = InterviewSession.objects.filter(user_id=sb_user.id).order_by('-created_at')[:limit]
            
            sessions_data = []
            for session in sessions:
                session_info = InterviewSessionSerializer(session).data
                
                # Get question count
                question_count = InterviewQuestion.objects.filter(session_id=session.id).count()
                session_info["question_count"] = question_count
                
                # Get completion stats
                answered_questions = InterviewAnswer.objects.filter(
                    question__session_id=session.id
                ).values_list('question_id', flat=True).distinct().count()
                session_info["answered_questions"] = answered_questions
                session_info["completion_rate"] = (answered_questions / question_count * 100) if question_count > 0 else 0
                
                # Get average score
                evaluations = InterviewEvaluation.objects.filter(
                    answer__question__session_id=session.id
                )
                if evaluations.exists():
                    avg_score = sum(e.overall_score for e in evaluations) / evaluations.count()
                    session_info["average_score"] = round(avg_score, 1)
                else:
                    session_info["average_score"] = None
                
                sessions_data.append(session_info)
            
            return Response({
                "sessions": sessions_data,
                "total_sessions": InterviewSession.objects.filter(user_id=sb_user.id).count(),
            }, status=200)


class InterviewProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's overall interview progress and statistics."""
        try:
            sb_user = SbUser.objects.get(email=request.user.email)
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        # Get overall statistics
        total_sessions = InterviewSession.objects.filter(user_id=sb_user.id).count()
        total_questions = InterviewQuestion.objects.filter(session__user_id=sb_user.id).count()
        total_answers = InterviewAnswer.objects.filter(question__session__user_id=sb_user.id).count()
        
        # Get average scores by category
        evaluations = InterviewEvaluation.objects.filter(
            answer__question__session__user_id=sb_user.id
        ).select_related('answer__question')
        
        category_scores = {}
        difficulty_scores = {}
        
        for evaluation in evaluations:
            category = evaluation.answer.question.category
            difficulty = evaluation.answer.question.difficulty
            
            if category not in category_scores:
                category_scores[category] = []
            if difficulty not in difficulty_scores:
                difficulty_scores[difficulty] = []
                
            category_scores[category].append(evaluation.overall_score)
            difficulty_scores[difficulty].append(evaluation.overall_score)
        
        # Calculate averages
        category_averages = {
            category: round(sum(scores) / len(scores), 1) 
            for category, scores in category_scores.items()
        }
        difficulty_averages = {
            difficulty: round(sum(scores) / len(scores), 1) 
            for difficulty, scores in difficulty_scores.items()
        }
        
        # Get recent performance trend (last 5 sessions)
        recent_sessions = InterviewSession.objects.filter(
            user_id=sb_user.id
        ).order_by('-created_at')[:5]
        
        performance_trend = []
        for session in recent_sessions:
            session_evaluations = InterviewEvaluation.objects.filter(
                answer__question__session_id=session.id
            )
            if session_evaluations.exists():
                avg_score = sum(e.overall_score for e in session_evaluations) / session_evaluations.count()
                performance_trend.append({
                    "session_id": str(session.id),
                    "date": session.created_at,
                    "average_score": round(avg_score, 1),
                    "question_count": session_evaluations.count()
                })
        
        return Response({
            "overall_stats": {
                "total_sessions": total_sessions,
                "total_questions": total_questions,
                "total_answers": total_answers,
                "completion_rate": (total_answers / total_questions * 100) if total_questions > 0 else 0,
            },
            "category_performance": category_averages,
            "difficulty_performance": difficulty_averages,
            "performance_trend": performance_trend,
        }, status=200)


# ==================== AUDIO INTERVIEW APIS ====================

class AudioInterviewQuestionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Generate AI-powered audio interview questions with TTS conversion.

        Body:
          - cv_id (optional): use stored CV
          - cv_text (optional): raw CV text
          - job_description (required): target job description
          - question_count (optional): number of questions (default 5)
          - difficulty (optional): easy/medium/hard (default medium)
          - voice_id (optional): TTS voice selection (default: alloy)
          - language (optional): language code (default: en)
        """
        cv_id = request.data.get("cv_id")
        cv_text = request.data.get("cv_text")
        job_description = request.data.get("job_description")
        question_count = int(request.data.get("question_count", 5))
        difficulty = request.data.get("difficulty", "medium")
        voice_id = request.data.get("voice_id", "alloy")  # OpenAI TTS voices: alloy, echo, fable, onyx, nova, shimmer
        language = request.data.get("language", "en")

        if not job_description:
            return Response({"detail": "job_description is required"}, status=400)

        # Resolve CV text (same logic as regular interview)
        try:
            sb_user = SbUser.objects.get(email=request.user.email)
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        if cv_id and not cv_text:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                return Response({"detail": "cv_id not found"}, status=404)

        if not cv_id and not cv_text:
            latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
            if not latest_cv:
                return Response({
                    "detail": "No uploaded CV found for the authenticated user",
                    "hint": "Upload a CV first using /api/rag/cv-upload/",
                }, status=404)
            cv_text = latest_cv.parsed_text or ""

        if not cv_text:
            return Response({"detail": "cv_text is empty"}, status=400)

        # Generate questions using AI (same as regular interview)
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        system_prompt = (
            "You are an expert interview coach and hiring manager. "
            "Generate personalized interview questions based on the candidate's CV and target job description. "
            "Return STRICT JSON with questions array. Each question should have: question, category, difficulty, tips, and expected_answer_focus. "
            "Base questions on the actual CV content and job requirements; make them specific and relevant."
        )
        user_prompt = (
            f"Candidate CV:\n{cv_text}\n\n"
            f"Target Job Description:\n{job_description}\n\n"
            f"Generate {question_count} {difficulty} difficulty interview questions in this JSON format:\n"
            '{"questions": [{"question": "Tell me about a challenging project you worked on", "category": "behavioral", "difficulty": "medium", "tips": "Use STAR method", "expected_answer_focus": "problem-solving and leadership"}]}'
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        except Exception as e:
            return Response({"detail": f"Model call failed: {e}"}, status=400)

        def _parse_json(s: str):
            try:
                return json.loads(s)
            except Exception:
                m = re.search(r"\{[\s\S]*\}", s)
                if m:
                    try:
                        return json.loads(m.group(0))
                    except Exception:
                        return None
                return None

        data = _parse_json(content)
        if not isinstance(data, dict):
            return Response({
                "detail": "Model returned non-JSON output",
                "raw": content,
            }, status=400)

        # Create audio interview session
        try:
            session = AudioInterviewSession.objects.create(
                user_id=sb_user.id,
                job_description=job_description,
                difficulty=difficulty,
                voice_id=voice_id,
                language=language,
                created_at=timezone.now(),
            )
            
            # Store each question and generate TTS audio
            stored_questions = []
            openai_api_key = config("OPENAI_API_KEY", default=None)
            
            for q in data.get("questions") or []:
                question_text = q.get("question", "")
                
                # Create question record first
                question_obj = AudioInterviewQuestion.objects.create(
                    session_id=session.id,
                    question=question_text,
                    category=q.get("category", ""),
                    difficulty=q.get("difficulty", difficulty),
                    tips=q.get("tips", ""),
                    expected_answer_focus=q.get("expected_answer_focus", ""),
                    created_at=timezone.now(),
                )
                
                # Generate TTS audio using ElevenLabs (alternative to OpenAI TTS)
                audio_file_path = None
                audio_duration = None
                
                elevenlabs_api_key = config("ELEVENLABS_API_KEY", default=None)
                
                if elevenlabs_api_key and question_text:
                    try:
                        # Generate audio using ElevenLabs API
                        elevenlabs_url = 'https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB'  # Alloy voice
                        elevenlabs_headers = {
                            'Accept': 'audio/mpeg',
                            'Content-Type': 'application/json',
                            'xi-api-key': elevenlabs_api_key
                        }
                        elevenlabs_data = {
                            'text': question_text,
                            'model_id': 'eleven_monolingual_v1',
                            'voice_settings': {
                                'stability': 0.5,
                                'similarity_boost': 0.5
                            }
                        }
                        
                        elevenlabs_response = requests.post(
                            elevenlabs_url, 
                            headers=elevenlabs_headers, 
                            json=elevenlabs_data, 
                            timeout=30
                        )
                        
                        if elevenlabs_response.ok:
                            # Save audio file
                            audio_filename = f"question_{question_obj.id}.mp3"
                            audio_content = ContentFile(elevenlabs_response.content, name=audio_filename)
                            audio_file_path = default_storage.save(f"audio/questions/{audio_filename}", audio_content)
                            
                            # Estimate duration (rough calculation: ~150 words per minute, ~5 chars per word)
                            estimated_duration = len(question_text) / (150 * 5 / 60)  # seconds
                            audio_duration = max(2.0, estimated_duration)  # minimum 2 seconds
                            
                            # Update question with audio info
                            question_obj.audio_file_path = audio_file_path
                            question_obj.audio_duration = audio_duration
                            question_obj.save(update_fields=["audio_file_path", "audio_duration"])
                            
                            print(f"✅ ElevenLabs TTS generated audio for question {question_obj.id}")
                        else:
                            print(f"ElevenLabs TTS API error: {elevenlabs_response.status_code} - {elevenlabs_response.text}")
                        
                    except Exception as e:
                        print(f"ElevenLabs TTS Error for question {question_obj.id}: {str(e)}")
                        # Fallback to browser TTS
                        pass
                
                stored_questions.append({
                    "id": str(question_obj.id),
                    "question": question_obj.question,
                    "category": question_obj.category,
                    "difficulty": question_obj.difficulty,
                    "tips": question_obj.tips,
                    "expected_answer_focus": question_obj.expected_answer_focus,
                    "audio_file_path": audio_file_path,
                    "audio_duration": audio_duration,
                    "has_audio": audio_file_path is not None,
                })
            
            result = {
                "session_id": str(session.id),
                "questions": stored_questions,
                "job_description": job_description,
                "difficulty": difficulty,
                "question_count": len(stored_questions),
                "voice_id": voice_id,
                "language": language,
                "instructions": "Listen to each question, record your audio answer, then use /api/audio-interview/submit-all-answers/ for batch evaluation.",
                "flow": "audio_batch_processing"
            }
            return Response(result, status=200)
            
        except Exception as e:
            return Response({"detail": f"Failed to create audio interview session: {str(e)}"}, status=400)


class AudioInterviewQuestionAudioView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, question_id):
        """Serve AI-generated audio file for a specific question.
        
        URL: /audio-interview/question/{question_id}/audio/
        """
        try:
            # Verify user owns this question
            sb_user = SbUser.objects.get(email=request.user.email)
            question = AudioInterviewQuestion.objects.get(
                id=question_id,
                session__user_id=sb_user.id
            )
            
            # Check if we have server-generated audio (ElevenLabs)
            if question.audio_file_path and default_storage.exists(question.audio_file_path):
                # Serve the audio file
                file_content = default_storage.open(question.audio_file_path).read()
                response = HttpResponse(file_content, content_type='audio/mpeg')
                response['Content-Disposition'] = f'inline; filename="question_{question_id}.mp3"'
                return response
            else:
                # Fallback to question text for client-side TTS
                return Response({
                    "question_text": question.question,
                    "voice_id": question.session.voice_id or "alloy",
                    "language": question.session.language
                })
                
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        except AudioInterviewQuestion.DoesNotExist:
            return Response({"detail": "Question not found or access denied"}, status=404)


class AudioInterviewAnswerSubmissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Submit audio answer for a question with transcription.

        Body:
          - question_id (required): question UUID
          - audio_file (required): recorded audio file (multipart/form-data)
          - transcribed_text (optional): client-side STT result
          - transcription_confidence (optional): STT confidence (0.0-1.0)
        """
        question_id = request.data.get("question_id")
        audio_file = request.FILES.get("audio_file")

        if not question_id:
            return Response({"detail": "question_id is required"}, status=400)
        
        # Allow text-only submissions for testing
        if not audio_file and not request.data.get("transcribed_text"):
            return Response({"detail": "Either audio_file or transcribed_text is required"}, status=400)

        try:
            # Verify user owns this question
            sb_user = SbUser.objects.get(email=request.user.email)
            question = AudioInterviewQuestion.objects.get(
                id=question_id,
                session__user_id=sb_user.id
            )
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        except AudioInterviewQuestion.DoesNotExist:
            return Response({"detail": "Question not found or access denied"}, status=404)

        # Handle audio file (if provided)
        audio_file_path = None
        audio_duration = None
        
        if audio_file:
            try:
                audio_filename = f"answer_{uuid.uuid4()}.{audio_file.name.split('.')[-1]}"
                audio_content = ContentFile(audio_file.read(), name=audio_filename)
                audio_file_path = default_storage.save(f"audio/answers/{audio_filename}", audio_content)
                
                # Get audio duration (rough estimate based on file size)
                audio_duration = len(audio_file.read()) / (16000 * 2)  # Assume 16kHz, 16-bit
                
            except Exception as e:
                return Response({"detail": f"Failed to save audio file: {str(e)}"}, status=400)

        # Handle transcription
        transcribed_text = request.data.get("transcribed_text", "")
        transcription_confidence = float(request.data.get("transcription_confidence", 0.9))
        
        # If no transcribed text provided and we have audio, use Whisper
        if not transcribed_text and audio_file:
            openai_api_key = config("OPENAI_API_KEY", default=None)
            
            if openai_api_key:
                try:
                    # Reset file pointer
                    audio_file.seek(0)
                    
                    whisper_url = "https://api.openai.com/v1/audio/transcriptions"
                    whisper_headers = {
                        "Authorization": f"Bearer {openai_api_key}",
                    }
                    whisper_files = {
                        "file": (audio_file.name, audio_file, audio_file.content_type),
                    }
                    whisper_data = {
                        "model": "whisper-1",
                        "language": question.session.language,
                        "response_format": "verbose_json"
                    }
                    
                    whisper_response = requests.post(
                        whisper_url, 
                        headers=whisper_headers, 
                        files=whisper_files, 
                        data=whisper_data, 
                        timeout=60
                    )
                    
                    if whisper_response.ok:
                        whisper_data = whisper_response.json()
                        transcribed_text = whisper_data.get("text", "")
                        # Whisper doesn't provide confidence in the simple response, estimate based on duration
                        transcription_confidence = min(0.95, max(0.7, len(transcribed_text) / max(1, audio_duration * 10)))
                    
                except Exception as e:
                    print(f"Whisper transcription error: {str(e)}")
                    transcribed_text = "[Transcription failed - please provide text manually]"
                    transcription_confidence = 0.0
            else:
                transcribed_text = "[Audio received - awaiting manual transcription]"
                transcription_confidence = 0.0

        # Store the answer
        try:
            # Check if answer already exists, update or create
            answer, created = AudioInterviewAnswer.objects.get_or_create(
                question_id=question_id,
                defaults={
                    'audio_file_path': audio_file_path or 'text-only-answer',
                    'transcribed_text': transcribed_text,
                    'audio_duration': audio_duration,
                    'transcription_confidence': transcription_confidence,
                    'submitted_at': timezone.now(),
                }
            )
            if not created:
                # Update existing answer
                answer.audio_file_path = audio_file_path or 'text-only-answer'
                answer.transcribed_text = transcribed_text
                answer.audio_duration = audio_duration
                answer.transcription_confidence = transcription_confidence
                answer.submitted_at = timezone.now()
                answer.save()
            
            return Response({
                "answer_id": str(answer.id),
                "question_id": str(question_id),
                "audio_file_path": audio_file_path,
                "transcribed_text": transcribed_text,
                "audio_duration": audio_duration,
                "transcription_confidence": transcription_confidence,
                "submitted_at": answer.submitted_at,
            }, status=201 if created else 200)
            
        except Exception as e:
            return Response({"detail": f"Failed to store answer: {str(e)}"}, status=400)


class AudioInterviewBatchSubmissionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Submit all audio answers for a session and get batch AI evaluation.

        Body:
          - session_id (required): audio interview session ID
          - answers (optional): array of {question_id, audio_file} - if not provided, uses stored audio answers
        """
        session_id = request.data.get("session_id")

        if not session_id:
            return Response({"detail": "session_id is required"}, status=400)

        try:
            # Verify user owns this session
            sb_user = SbUser.objects.get(email=request.user.email)
            session = AudioInterviewSession.objects.get(id=session_id, user_id=sb_user.id)
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        except AudioInterviewSession.DoesNotExist:
            return Response({"detail": "Session not found or access denied"}, status=404)

        # Get all questions for this session
        questions = AudioInterviewQuestion.objects.filter(session_id=session_id)
        question_dict = {str(q.id): q for q in questions}

        # Get all submitted answers for this session
        submitted_answers = AudioInterviewAnswer.objects.filter(question__session_id=session_id)
        
        if not submitted_answers.exists():
            return Response({"detail": "No audio answers found for this session"}, status=400)

        # Prepare data for batch evaluation
        stored_answers = []
        for answer in submitted_answers:
            question = question_dict.get(str(answer.question_id))
            if question:
                stored_answers.append({
                    'answer_id': str(answer.id),
                    'question_id': str(answer.question_id),
                    'question': question.question,
                    'transcribed_text': answer.transcribed_text or "",
                    'answer_obj': answer
                })

        if not stored_answers:
            return Response({"detail": "No valid transcribed answers to process"}, status=400)

        # Get CV context for evaluation
        cv_text = ""
        latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
        if latest_cv:
            cv_text = latest_cv.parsed_text or ""

        # Call Fireworks for batch evaluation (same as regular interview)
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not set",
                "hint": "Configure FIREWORKS_API_KEY in environment",
            }, status=400)

        # Prepare batch evaluation prompt
        system_prompt = (
            "You are an expert interview coach providing comprehensive feedback on a complete audio interview session. "
            "The answers were transcribed from audio recordings, so consider potential transcription errors. "
            "Analyze all questions and answers together to provide holistic evaluation. "
            "Return STRICT JSON with evaluations array. Each evaluation should have: "
            "overall_score (0-100), strengths (array), weaknesses (array), "
            "correct_answer (string), answer_analysis (string), improvement_tips (array), "
            "follow_up_questions (array). "
            "Consider the flow and consistency across all answers, and account for the audio format."
        )

        # Build context for all Q&A pairs
        qa_context = []
        for i, answer_data in enumerate(stored_answers, 1):
            qa_context.append(
                f"Question {i}: {answer_data['question']}\n"
                f"Candidate's Answer {i} (transcribed from audio): {answer_data['transcribed_text']}"
            )

        user_prompt = (
            f"Candidate Background:\n{cv_text}\n\n"
            f"Job Description:\n{session.job_description}\n\n"
            f"Audio Interview Session (Complete - transcribed from speech):\n" + "\n\n".join(qa_context) + "\n\n"
            "Provide comprehensive evaluation for each answer in this JSON format:\n"
            '{"evaluations": [{"overall_score": 85, "strengths": ["Clear examples", "Good structure"], '
            '"weaknesses": ["Could be more specific", "Minor transcription unclear"], '
            '"correct_answer": "The ideal answer would include...", '
            '"answer_analysis": "Your response demonstrates...", '
            '"improvement_tips": ["Add specific metrics", "Speak more clearly for better transcription"], '
            '"follow_up_questions": ["Can you elaborate on...", "What was the impact of..."]}]}'
        )

        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            model_name = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p1-70b-instruct")
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            }
            r = requests.post(url, headers=headers, json=payload, timeout=120)
            if not r.ok:
                return Response({"detail": f"Fireworks error: {r.status_code}", "body": r.text}, status=400)
            
            data_resp = r.json()
            content = data_resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            
            def _parse_json(s: str):
                try:
                    return json.loads(s)
                except Exception:
                    m = re.search(r"\{[\s\S]*\}", s)
                    if m:
                        try:
                            return json.loads(m.group(0))
                        except Exception:
                            return None
                    return None

            evaluation_data = _parse_json(content)
            if not isinstance(evaluation_data, dict) or "evaluations" not in evaluation_data:
                return Response({
                    "detail": "Model returned invalid evaluation format",
                    "raw": content,
                }, status=400)

            evaluations = evaluation_data.get("evaluations", [])
            
            # Store evaluations in database
            stored_evaluations = []
            for i, eval_data in enumerate(evaluations):
                if i >= len(stored_answers):
                    break
                    
                answer_obj = stored_answers[i]['answer_obj']
                
                # Delete existing evaluation if any
                AudioInterviewEvaluation.objects.filter(answer_id=answer_obj.id).delete()
                
                # Create new evaluation
                evaluation = AudioInterviewEvaluation.objects.create(
                    answer_id=answer_obj.id,
                    overall_score=eval_data.get("overall_score", 0),
                    strengths=eval_data.get("strengths", []),
                    weaknesses=eval_data.get("weaknesses", []),
                    correct_answer=eval_data.get("correct_answer", ""),
                    answer_analysis=eval_data.get("answer_analysis", ""),
                    improvement_tips=eval_data.get("improvement_tips", []),
                    follow_up_questions=eval_data.get("follow_up_questions", []),
                    evaluated_at=timezone.now(),
                )
                
                stored_evaluations.append({
                    "evaluation_id": str(evaluation.id),
                    "answer_id": str(answer_obj.id),
                    "question_id": stored_answers[i]['question_id'],
                    "question": stored_answers[i]['question'],
                    "transcribed_text": stored_answers[i]['transcribed_text'],
                    "audio_duration": answer_obj.audio_duration,
                    "transcription_confidence": answer_obj.transcription_confidence,
                    "evaluation": AudioInterviewEvaluationSerializer(evaluation).data
                })

            # Calculate session statistics
            scores = [eval_data.get("overall_score", 0) for eval_data in evaluations if eval_data.get("overall_score")]
            average_score = sum(scores) / len(scores) if scores else 0
            
            return Response({
                "session_id": str(session_id),
                "total_questions": len(stored_answers),
                "total_evaluations": len(stored_evaluations),
                "average_score": round(average_score, 1),
                "evaluations": stored_evaluations,
                "session_complete": True,
                "interview_type": "audio",
                "voice_id": session.voice_id,
                "language": session.language,
                "message": "All audio answers evaluated successfully using batch AI processing"
            }, status=200)

        except Exception as e:
            return Response({"detail": f"Audio batch evaluation failed: {str(e)}"}, status=400)


class AudioInterviewEvaluationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, answer_id):
        """Get evaluation for a specific answer.
        
        URL: /audio-interview/evaluation/{answer_id}/
        """
        try:
            # Verify user owns this answer
            sb_user = SbUser.objects.get(email=request.user.email)
            answer = AudioInterviewAnswer.objects.get(
                id=answer_id,
                question__session__user_id=sb_user.id
            )
            
            # Get evaluation
            try:
                evaluation = AudioInterviewEvaluation.objects.get(answer=answer)
                return Response(AudioInterviewEvaluationSerializer(evaluation).data)
            except AudioInterviewEvaluation.DoesNotExist:
                return Response({"detail": "No evaluation found for this answer"}, status=404)
                
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        except AudioInterviewAnswer.DoesNotExist:
            return Response({"detail": "Answer not found or access denied"}, status=404)


class AudioInterviewSessionEvaluationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        """Get all evaluations for a session.
        
        URL: /audio-interview/session/{session_id}/evaluations/
        """
        try:
            # Verify user owns this session
            sb_user = SbUser.objects.get(email=request.user.email)
            session = AudioInterviewSession.objects.get(id=session_id, user_id=sb_user.id)
            
            # Get all evaluations for this session
            evaluations = AudioInterviewEvaluation.objects.filter(
                answer__question__session_id=session_id
            ).order_by('evaluated_at')
            
            evaluations_data = []
            for evaluation in evaluations:
                eval_data = AudioInterviewEvaluationSerializer(evaluation).data
                eval_data['question_id'] = str(evaluation.answer.question_id)
                eval_data['question'] = evaluation.answer.question.question
                eval_data['transcribed_text'] = evaluation.answer.transcribed_text
                eval_data['answer_id'] = str(evaluation.answer.id)
                evaluations_data.append(eval_data)
            
            # Calculate session statistics
            scores = [e.overall_score for e in evaluations if e.overall_score]
            average_score = sum(scores) / len(scores) if scores else 0
            
            return Response({
                "session_id": str(session_id),
                "total_evaluations": len(evaluations_data),
                "average_score": round(average_score, 1),
                "evaluations": evaluations_data,
                "interview_type": "audio"
            })
                
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)
        except AudioInterviewSession.DoesNotExist:
            return Response({"detail": "Session not found or access denied"}, status=404)


class AudioInterviewHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get user's audio interview history and progress.

        Query params:
          - limit (optional): number of sessions to return (default: 10)
          - session_id (optional): get specific session details
        """
        try:
            sb_user = SbUser.objects.get(email=request.user.email)
        except SbUser.DoesNotExist:
            return Response({"detail": "User not found"}, status=404)

        limit = int(request.query_params.get("limit", 10))
        session_id = request.query_params.get("session_id")

        if session_id:
            # Get specific session with all details
            try:
                session = AudioInterviewSession.objects.get(id=session_id, user_id=sb_user.id)
                questions = AudioInterviewQuestion.objects.filter(session_id=session.id)
                
                session_data = {
                    "session": AudioInterviewSessionSerializer(session).data,
                    "questions": []
                }
                
                for question in questions:
                    question_data = AudioInterviewQuestionSerializer(question).data
                    
                    # Get answers and evaluations for this question
                    answers = AudioInterviewAnswer.objects.filter(question_id=question.id)
                    question_data["answers"] = []
                    
                    for answer in answers:
                        answer_data = AudioInterviewAnswerSerializer(answer).data
                        
                        # Get evaluation for this answer
                        try:
                            evaluation = AudioInterviewEvaluation.objects.get(answer_id=answer.id)
                            answer_data["evaluation"] = AudioInterviewEvaluationSerializer(evaluation).data
                        except AudioInterviewEvaluation.DoesNotExist:
                            answer_data["evaluation"] = None
                        
                        question_data["answers"].append(answer_data)
                    
                    session_data["questions"].append(question_data)
                
                return Response(session_data, status=200)
                
            except AudioInterviewSession.DoesNotExist:
                return Response({"detail": "Audio session not found"}, status=404)
        
        else:
            # Get session summary
            sessions = AudioInterviewSession.objects.filter(user_id=sb_user.id).order_by('-created_at')[:limit]
            sessions_data = []
            
            for session in sessions:
                questions = AudioInterviewQuestion.objects.filter(session_id=session.id)
                answers = AudioInterviewAnswer.objects.filter(question__session_id=session.id)
                evaluations = AudioInterviewEvaluation.objects.filter(answer__question__session_id=session.id)
                
                avg_score = 0
                if evaluations.exists():
                    avg_score = sum(e.overall_score for e in evaluations) / evaluations.count()
                
                sessions_data.append({
                    "id": str(session.id),
                    "user": str(session.user_id),
                    "job_description": session.job_description[:100] + "..." if len(session.job_description) > 100 else session.job_description,
                    "difficulty": session.difficulty,
                    "voice_id": session.voice_id,
                    "language": session.language,
                    "created_at": session.created_at,
                    "question_count": questions.count(),
                    "answered_questions": answers.count(),
                    "completion_rate": (answers.count() / questions.count() * 100) if questions.count() > 0 else 0,
                    "average_score": round(avg_score, 1),
                    "interview_type": "audio"
                })
            
            return Response({
                "sessions": sessions_data,
                "total_sessions": AudioInterviewSession.objects.filter(user_id=sb_user.id).count(),
                "interview_type": "audio"
            }, status=200)