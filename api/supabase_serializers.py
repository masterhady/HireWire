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

    class Meta:
        model = Application
        fields = "__all__"
        extra_fields = ["job_title", "company_name", "cv_filename"]

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