from rest_framework import serializers
from .supabase_models import (
    SbCompany,
    SbUser,
    Skill,
    CV,
    CVEmbedding,
    Job,
    JobEmbedding,
    Application,
    ApplicationStatus,
    ApplicationNote,
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


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = SbCompany
        fields = "__all__"


class SbUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SbUser
        fields = "__all__"


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = "__all__"


class CVSerializer(serializers.ModelSerializer):
    class Meta:
        model = CV
        fields = "__all__"


class CVEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = CVEmbedding
        fields = "__all__"
        read_only_fields = ("embedding",)


class JobSerializer(serializers.ModelSerializer):
    company_display = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = "__all__"
        extra_fields = ["company_display"]

    def get_company_display(self, obj):
        # Try to derive a human-friendly company label from the AUTH_USER related object
        try:
            user = getattr(obj, "company", None)
            if not user:
                return None
            # Prefer full name or username/email if available
            for attr in ["get_full_name", "full_name"]:
                val = getattr(user, attr, None)
                if callable(val):
                    name = val()
                    if name:
                        return name
                elif val:
                    return val
            if getattr(user, "username", None):
                return user.username
            if getattr(user, "email", None):
                return user.email
        except Exception:
            pass
        return None


class JobEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobEmbedding
        fields = "__all__"
        read_only_fields = ("embedding",)


class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.SerializerMethodField()
    company_name = serializers.SerializerMethodField()
    cv_filename = serializers.SerializerMethodField()
    current_status = serializers.SerializerMethodField()
    status_history = serializers.SerializerMethodField()
    notes_count = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = "__all__"
        extra_fields = ["job_title", "company_name", "cv_filename", "current_status", "status_history", "notes_count"]

    def get_job_title(self, obj):
        try:
            return getattr(obj.job, "title", None)
        except Exception:
            return None

    def get_company_name(self, obj):
        try:
            return getattr(obj.company, "name", None)
        except Exception:
            return None

    def get_cv_filename(self, obj):
        try:
            return getattr(obj.cv, "filename", None)
        except Exception:
            return None
    
    def get_current_status(self, obj):
        try:
            latest_status = ApplicationStatus.objects.filter(application=obj).first()
            if latest_status:
                return {
                    'status': latest_status.status,
                    'status_display': latest_status.get_status_display(),
                    'updated_at': latest_status.updated_at.isoformat() if latest_status.updated_at else None,
                }
        except Exception:
            pass
        return {'status': 'applied', 'status_display': 'Applied', 'updated_at': None}
    
    def get_status_history(self, obj):
        try:
            statuses = ApplicationStatus.objects.filter(application=obj).order_by('-created_at')[:10]
            return [
                {
                    'status': s.status,
                    'status_display': s.get_status_display(),
                    'notes': s.notes,
                    'created_at': s.created_at.isoformat() if s.created_at else None,
                }
                for s in statuses
            ]
        except Exception:
            return []
    
    def get_notes_count(self, obj):
        try:
            return ApplicationNote.objects.filter(application=obj).count()
        except Exception:
            return 0


class ApplicationStatusSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ApplicationStatus
        fields = "__all__"
        read_only_fields = ['id', 'created_at', 'updated_at']


class ApplicationNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationNote
        fields = "__all__"
        read_only_fields = ['id', 'created_at', 'updated_at']


class RecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recommendation
        fields = "__all__"


class InterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewSession
        fields = "__all__"


class InterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewQuestion
        fields = "__all__"


class InterviewAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewAnswer
        fields = "__all__"


class InterviewEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterviewEvaluation
        fields = "__all__"


class AudioInterviewSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioInterviewSession
        fields = "__all__"


class AudioInterviewQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioInterviewQuestion
        fields = "__all__"


class AudioInterviewAnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioInterviewAnswer
        fields = "__all__"


class AudioInterviewEvaluationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AudioInterviewEvaluation
        fields = "__all__"