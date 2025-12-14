from rest_framework import serializers
from .resume_models import Resume, WorkExperience, Education, ResumeSkill, ResumeProject

class WorkExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkExperience
        fields = ['id', 'job_title', 'company', 'start_date', 'end_date', 'is_current', 'description']

class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'degree', 'institution', 'start_date', 'end_date', 'description']

class ResumeSkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeSkill
        fields = ['id', 'name', 'level']

class ResumeProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumeProject
        fields = ['id', 'name', 'description', 'url']

class ResumeSerializer(serializers.ModelSerializer):
    work_experience = WorkExperienceSerializer(many=True)
    education = EducationSerializer(many=True)
    skills = ResumeSkillSerializer(many=True)
    projects = ResumeProjectSerializer(many=True)

    class Meta:
        model = Resume
        fields = ['id', 'title', 'full_name', 'email', 'phone', 'summary', 'linkedin_url', 'portfolio_url', 'created_at', 'updated_at', 'work_experience', 'education', 'skills', 'projects']
        read_only_fields = ['created_at', 'updated_at']

    def create(self, validated_data):
        work_experience_data = validated_data.pop('work_experience', [])
        education_data = validated_data.pop('education', [])
        skills_data = validated_data.pop('skills', [])
        projects_data = validated_data.pop('projects', [])

        resume = Resume.objects.create(**validated_data)

        for item in work_experience_data:
            WorkExperience.objects.create(resume=resume, **item)
        for item in education_data:
            Education.objects.create(resume=resume, **item)
        for item in skills_data:
            ResumeSkill.objects.create(resume=resume, **item)
        for item in projects_data:
            ResumeProject.objects.create(resume=resume, **item)

        return resume

    def update(self, instance, validated_data):
        work_experience_data = validated_data.pop('work_experience', [])
        education_data = validated_data.pop('education', [])
        skills_data = validated_data.pop('skills', [])
        projects_data = validated_data.pop('projects', [])

        # Update main fields
        instance.title = validated_data.get('title', instance.title)
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.email = validated_data.get('email', instance.email)
        instance.phone = validated_data.get('phone', instance.phone)
        instance.summary = validated_data.get('summary', instance.summary)
        instance.linkedin_url = validated_data.get('linkedin_url', instance.linkedin_url)
        instance.portfolio_url = validated_data.get('portfolio_url', instance.portfolio_url)
        instance.save()

        # Helper to update nested relations
        def update_nested(model, serializer_cls, current_items, new_data):
            # Delete missing items
            # This is a simple full replacement strategy for simplicity in this MVP
            # A more robust approach would match by ID to update existing ones
            current_items.all().delete()
            for item in new_data:
                model.objects.create(resume=instance, **item)

        update_nested(WorkExperience, WorkExperienceSerializer, instance.work_experience, work_experience_data)
        update_nested(Education, EducationSerializer, instance.education, education_data)
        update_nested(ResumeSkill, ResumeSkillSerializer, instance.skills, skills_data)
        update_nested(ResumeProject, ResumeProjectSerializer, instance.projects, projects_data)

        return instance
