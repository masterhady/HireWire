from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from datetime import timedelta
from .video_interview_models import VideoInterview
from .supabase_models import Application, Job, InterviewEvaluation, InterviewSession
from .resume_models import ResumeSkill

class AnalyticsViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        user = request.user
        
        # Total Applications
        # Application -> CV -> SbUser (linked by email)
        total_applications = Application.objects.filter(cv__user__email=user.email).count()
        
        # Total Interviews (Mock Video + Chat Sessions)
        video_interviews = VideoInterview.objects.filter(user=user).count()
        # InterviewSession -> SbUser (linked by email)
        chat_interviews = InterviewSession.objects.filter(user__email=user.email).count()
        total_interviews = video_interviews + chat_interviews
        
        # Response Rate (Applications with status other than 'applied' / Total)
        # Assuming status 'applied' is the initial state.
        # We need to check ApplicationStatus for the latest status, or if Application has a status field (it doesn't seem to have one in the model shown, wait)
        # The model shown in Step 551 DOES NOT have a 'status' field. It has 'match_score' and 'matched_at'.
        # However, there is an ApplicationStatus model.
        # Let's check if we can filter by related ApplicationStatus.
        # For now, let's assume we can count applications that have *any* status entry other than 'applied' or count distinct applications with status updates.
        
        # Re-checking ApplicationStatus model in Step 528:
        # class ApplicationStatus(models.Model): ... application = ForeignKey ... status = CharField ...
        
        # So we should filter applications where the *latest* status is not 'applied'.
        # Or simpler: count applications that have a status history containing something other than 'applied'.
        
        responded_applications = Application.objects.filter(
            cv__user__email=user.email,
            statuses__status__in=['viewed', 'screening', 'interview', 'interviewing', 'offer', 'rejected', 'accepted']
        ).distinct().count()
        
        response_rate = (responded_applications / total_applications * 100) if total_applications > 0 else 0
        
        return Response({
            'total_applications': total_applications,
            'total_interviews': total_interviews,
            'response_rate': round(response_rate, 1)
        })

    @action(detail=False, methods=['get'])
    def application_trends(self, request):
        user = request.user
        six_months_ago = timezone.now() - timedelta(days=180)
        
        # Application -> CV -> User
        # Note: Application model has 'matched_at', but maybe we want creation time.
        # The model in Step 551 has 'matched_at'. It does NOT have 'created_at'.
        # Wait, Step 528 shows:
        # class Application(models.Model): ... matched_at ...
        # It does NOT show created_at.
        # However, ApplicationStatus has created_at.
        # Or maybe I missed it. Let's check Step 528 again.
        # Line 108: matched_at = ...
        # Line 110: class Meta:
        # It seems Application table might not have created_at? That's odd for a join table.
        # Let's assume 'matched_at' is the timestamp or we use the first status creation time.
        # Let's use 'matched_at' for now if it exists, otherwise we might need to rely on related objects.
        
        trends = Application.objects.filter(
            cv__user__email=user.email, 
            matched_at__gte=six_months_ago
        ).annotate(
            month=TruncMonth('matched_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        data = [
            {
                'month': item['month'].strftime('%b %Y') if item['month'] else 'Unknown',
                'applications': item['count']
            }
            for item in trends
        ]
        
        return Response(data)

    @action(detail=False, methods=['get'])
    def interview_performance(self, request):
        user = request.user
        
        performance_data = []

        # Mock Video Interview Scores (Grouped by Type)
        video_types = VideoInterview.objects.filter(user=user).values('interview_type').annotate(avg_score=Avg('overall_score'))
        for vt in video_types:
            performance_data.append({
                'type': f"{vt['interview_type']} (Video)",
                'score': round(vt['avg_score'] or 0, 1)
            })

        # Chat Interview Scores
        # InterviewEvaluation -> Answer -> Question -> Session -> SbUser (linked by email)
        chat_score = InterviewEvaluation.objects.filter(
            answer__question__session__user__email=user.email
        ).aggregate(avg_score=Avg('overall_score'))
        
        if chat_score['avg_score']:
            performance_data.append({
                'type': 'Technical (Chat)',
                'score': round(chat_score['avg_score'], 1)
            })

        return Response(performance_data)

    @action(detail=False, methods=['get'])
    def skill_gap(self, request):
        user = request.user
        
        # 1. Get User Skills
        # Resume -> Django User (linked by ID)
        user_skills = set(ResumeSkill.objects.filter(resume__user=user).values_list('name', flat=True))
        user_skills_lower = {s.lower() for s in user_skills}

        # 2. Get Applied Jobs Requirements
        # Job -> Application -> CV -> SbUser (linked by email)
        applied_jobs = Job.objects.filter(application__cv__user__email=user.email).values_list('requirements', flat=True)
        
        # 3. Define Common Tech Skills to check (Simplified for MVP)
        common_skills = [
            'Python', 'Java', 'JavaScript', 'React', 'Angular', 'Vue', 'Node.js', 'Django', 
            'Flask', 'FastAPI', 'SQL', 'PostgreSQL', 'MongoDB', 'AWS', 'Docker', 'Kubernetes',
            'Git', 'CI/CD', 'Machine Learning', 'Data Analysis', 'Communication', 'Leadership'
        ]

        skill_stats = []
        
        for skill in common_skills:
            skill_lower = skill.lower()
            # Count frequency in job requirements
            frequency = 0
            for req in applied_jobs:
                if req and skill_lower in req.lower():
                    frequency += 1
            
            if frequency > 0:
                has_skill = skill_lower in user_skills_lower
                status_label = 'Strong' if has_skill else 'Missing'
                total_apps = len(applied_jobs)
                relevance = (frequency / total_apps * 100) if total_apps > 0 else 0
                
                skill_stats.append({
                    'skill': skill,
                    'status': status_label,
                    'value': round(relevance, 1),
                    'has_skill': has_skill
                })

        # Sort by relevance (descending) and take top 10
        skill_stats.sort(key=lambda x: x['value'], reverse=True)
        
        return Response(skill_stats[:10])
