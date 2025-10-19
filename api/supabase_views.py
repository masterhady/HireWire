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