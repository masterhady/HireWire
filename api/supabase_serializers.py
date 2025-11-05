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
    class Meta:
        model = Job
        fields = "__all__"


class JobEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobEmbedding
        fields = "__all__"
        read_only_fields = ("embedding",)


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = "__all__"


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