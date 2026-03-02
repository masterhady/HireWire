from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
import requests
import json
import re
from decouple import config

from .resume_models import Resume, WorkExperience, Education, ResumeSkill, ResumeProject
from .resume_serializers import (
    ResumeSerializer, WorkExperienceSerializer, EducationSerializer, 
    ResumeSkillSerializer, ResumeProjectSerializer
)
from .supabase_models import CV, SbUser
from .rag import FIREWORKS_API_KEY, FIREWORKS_BASE_URL

CHAT_MODEL = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p3-70b-instruct")

def generate_text_fireworks(prompt, system_prompt="You are a helpful AI assistant."):
    if not FIREWORKS_API_KEY:
        return "Error: Fireworks API key not configured."
    
    url = f"{FIREWORKS_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {FIREWORKS_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generating text: {str(e)}"

class ResumeViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Resume.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=["post"], url_path="generate-summary")
    def generate_summary(self, request):
        job_title = request.data.get("job_title")
        skills = request.data.get("skills", [])
        experience = request.data.get("experience", [])
        
        prompt = f"Generate a professional resume summary for a {job_title}. \n"
        if skills:
            prompt += f"Key skills: {', '.join(skills)}. \n"
        if experience:
            prompt += f"Experience highlights: {experience}. \n"
            
        summary = generate_text_fireworks(prompt, system_prompt="You are a professional career coach helping write a resume.")
        return Response({"summary": summary})

    @action(detail=False, methods=["post"], url_path="enhance-experience")
    def enhance_experience(self, request):
        description = request.data.get("description")
        job_title = request.data.get("job_title")
        
        prompt = f"Rewrite the following work experience description for a {job_title} role to be more impactful, using action verbs and quantifying achievements where possible:\n\n{description}"
        
        enhanced = generate_text_fireworks(prompt, system_prompt="You are a professional resume writer.")
        return Response({"enhanced_description": enhanced})

    @action(detail=False, methods=["post"], url_path="suggest-skills")
    def suggest_skills(self, request):
        job_title = request.data.get("job_title")
        description = request.data.get("description", "")
        
        prompt = f"Suggest a list of 10 relevant technical and soft skills for a {job_title} role."
        if description:
            prompt += f" Based on this job description: {description}"
        
        skills_text = generate_text_fireworks(prompt, system_prompt="You are a hiring manager. List only the skills, separated by commas.")
        # Simple parsing, might need more robustness
        skills = [s.strip() for s in skills_text.split(',')]
        return Response({"skills": skills})
    
    @action(detail=False, methods=["post"], url_path="auto-fill-from-cv")
    def auto_fill_from_cv(self, request):
        """Extract data from user's uploaded CV and format it for resume fields"""
        cv_id = request.data.get("cv_id")
        
        # Resolve CV text
        cv_text = None
        if cv_id:
            try:
                cv_obj = CV.objects.get(id=cv_id)
                cv_text = cv_obj.parsed_text or ""
            except CV.DoesNotExist:
                return Response({"detail": "cv_id not found"}, status=404)
        
        if not cv_text:
            # Get latest CV for authenticated user
            auth_user = getattr(request, "user", None)
            auth_email = getattr(auth_user, "email", None)
            sb_user = None
            if auth_email:
                sb_user = SbUser.objects.filter(email=auth_email).first()
            
            if not sb_user:
                return Response({
                    "detail": "Associated Supabase user not found",
                    "hint": "Ensure a matching SbUser exists with the same email"
                }, status=404)
            
            latest_cv = CV.objects.filter(user_id=sb_user.id).order_by('-created_at').first()
            if not latest_cv:
                return Response({
                    "detail": "No uploaded CV found",
                    "hint": "Upload a CV first using /api/rag/cv-upload/"
                }, status=404)
            cv_text = latest_cv.parsed_text or ""
        
        if not cv_text:
            return Response({"detail": "CV text is empty"}, status=400)
        
        # Use CV extraction logic similar to CVRecommendationsView
        if not FIREWORKS_API_KEY:
            return Response({
                "detail": "FIREWORKS_API_KEY is not configured",
                "hint": "Configure FIREWORKS_API_KEY to use auto-fill feature"
            }, status=400)
        
        system_prompt = (
            "You are an expert resume data extractor. Given raw CV text, extract structured data and return ONLY valid JSON. "
            "Return JSON with: full_name (string), email (string), phone (string), summary (string), "
            "work_experience (array of objects with: job_title, company, start_date, end_date, description), "
            "education (array of objects with: degree, institution, start_date, end_date), "
            "skills (array of strings). Dates should be in YYYY-MM format or YYYY if only year available. "
            "Description should be a single string combining all bullets/points for that experience."
        )
        user_prompt = (
            f"CV Text:\n{cv_text[:8000]}\n\n"
            "Extract all relevant information and return as JSON. "
            "If information is missing, use null or empty array."
        )
        
        try:
            url = f"{FIREWORKS_BASE_URL}/chat/completions"
            headers = {
                "Authorization": f"Bearer {FIREWORKS_API_KEY}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": CHAT_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            }
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            
            # Parse JSON response
            try:
                extracted = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from response
                json_match = re.search(r'\{[\s\S]*\}', content)
                if json_match:
                    extracted = json.loads(json_match.group(0))
                else:
                    return Response({"detail": "Failed to parse extraction response"}, status=400)
            
            # Format response for resume form
            result = {
                "full_name": extracted.get("full_name") or "",
                "email": extracted.get("email") or "",
                "phone": extracted.get("phone") or "",
                "summary": extracted.get("summary") or "",
                "work_experience": extracted.get("work_experience") or [],
                "education": extracted.get("education") or [],
                "skills": extracted.get("skills") or [],
            }
            
            return Response(result, status=200)
            
        except requests.exceptions.RequestException as e:
            return Response({
                "detail": f"Failed to extract CV data: {str(e)}",
                "hint": "Check API configuration or try again later"
            }, status=500)
        except Exception as e:
            return Response({
                "detail": f"Error during extraction: {str(e)}"
            }, status=500)

class WorkExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = WorkExperienceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return WorkExperience.objects.filter(resume__user=self.request.user)

class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Education.objects.filter(resume__user=self.request.user)

class ResumeSkillViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeSkillSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ResumeSkill.objects.filter(resume__user=self.request.user)

class ResumeProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ResumeProjectSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ResumeProject.objects.filter(resume__user=self.request.user)
