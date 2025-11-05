# -*- coding: utf-8 -*-

import requests
from datetime import datetime, timedelta
import random

API_URL = "http://localhost:8000/api/jobs/"  # غيّري حسب السيرفر
TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYxNjYzNjczLCJpYXQiOjE3NjE2NjAwNzMsImp0aSI6IjhmN2I3ODI5NGIwZjQ1MmRhZjBhMGZhYzBiYzY3MjllIiwidXNlcl9pZCI6IjE5Iiwicm9sZSI6ImNvbXBhbnkiLCJ1c2VybmFtZSI6ImFjbWVfb3duZXIxIn0.gPH9Vyj2WiD9lLN5f-gNzulUq6W9wZi3VZlpAAEY_z4"

headers = {"Authorization": TOKEN} if TOKEN else {}

# بيانات لتوليد الوظائف تلقائيًا
titles = [
    "Odoo Developer", "React Developer", "Backend Engineer", "AI Engineer",
    "Data Scientist", "ML Researcher", "DevOps Engineer", "Frontend Developer",
    "Full Stack Developer", "Mobile App Developer", "UX/UI Designer", "QA Tester",
    "Project Manager", "Product Owner", "Business Analyst", "Marketing Specialist",
    "Social Media Manager", "Content Creator", "Copywriter", "Graphic Designer",
    "HR Specialist", "Recruitment Officer", "Finance Analyst", "Accountant",
    "Customer Support", "Data Engineer", "Database Admin", "Cybersecurity Engineer",
    "NLP Engineer", "Generative AI Specialist"
]

descriptions = [
    "Work on scalable solutions for enterprise clients.",
    "Develop innovative AI-based features.",
    "Design, build, and maintain modern APIs.",
    "Collaborate with cross-functional teams to deliver products.",
    "Ensure performance and reliability across systems.",
    "Participate in architecture and code reviews.",
    "Contribute to product design and user experience.",
    "Build automation and CI/CD pipelines.",
    "Research and implement modern web technologies.",
    "Optimize backend performance and query efficiency."
]

requirements = [
    "Python, Django, REST", "React, TypeScript, Tailwind",
    "PostgreSQL, Supabase, SQL", "Odoo, ERP, Backend",
    "Machine Learning, NLP", "LLM, RAG, FastAPI",
    "AWS, Docker, CI/CD", "UI/UX, Figma, Accessibility",
    "Git, Agile, Scrum", "Linux, Shell, Security"
]

# توليد 30 وظيفة
jobs = []
for i in range(30):
    job = {
        "company": 19,
        "title": titles[i],
        "description": random.choice(descriptions),
        "requirements": random.choice(requirements),
        "posted_at": (datetime(2025, 10, 2) + timedelta(days=i)).isoformat() + "Z",
        "is_active": True
    }
    jobs.append(job)

# إرسال الوظائف إلى الـ API
for idx, job in enumerate(jobs, start=1):
    res = requests.post(API_URL, json=job, headers=headers)
    if res.status_code in [200, 201]:
        print(f"✅ [{idx}] {job['title']} added successfully.")
    else:
        print(f"❌ [{idx}] Failed to add {job['title']} ({res.status_code}): {res.text}")
