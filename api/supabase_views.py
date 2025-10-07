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
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cv_text = request.data.get("cv_text")
        top_n = int(request.data.get("top_n", 5))
        similarity_threshold = float(request.data.get("similarity_threshold", 0.3))
        must_contain = request.data.get("must_contain") or []
        must_not_contain = request.data.get("must_not_contain") or []

        # Support file upload: .txt (plain), .pdf (PyPDF2), .docx (python-docx)
        if not cv_text and hasattr(request, 'FILES'):
            f = request.FILES.get('file') or request.FILES.get('cv_file')
            if f is not None:
                try:
                    name = getattr(f, 'name', '') or ''
                    lower_name = name.lower()
                    content_type = getattr(f, 'content_type', '') or ''
                    # Read bytes once
                    content = f.read()
                    # Try by extension/content-type
                    if lower_name.endswith('.txt') or content_type.startswith('text/'):
                        try:
                            cv_text = content.decode('utf-8')
                        except Exception:
                            cv_text = content.decode('latin-1', errors='ignore')
                    elif lower_name.endswith('.pdf') or 'pdf' in content_type:
                        try:
                            # Lazy import; optional dependency
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
                            # Lazy import; optional dependency
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

        if not cv_text:
            return Response({"detail": "cv_text or file is required"}, status=400)

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