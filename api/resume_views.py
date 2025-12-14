from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
import requests
from decouple import config

from .resume_models import Resume, WorkExperience, Education, ResumeSkill, ResumeProject
from .resume_serializers import (
    ResumeSerializer, WorkExperienceSerializer, EducationSerializer, 
    ResumeSkillSerializer, ResumeProjectSerializer
)

FIREWORKS_API_KEY = config("FIREWORKS_API_KEY", default=None)
FIREWORKS_BASE_URL = config("FIREWORKS_BASE_URL", default="https://api.fireworks.ai/inference/v1")
CHAT_MODEL = "accounts/fireworks/models/llama-v3p1-70b-instruct"

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
