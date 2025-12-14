from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .video_interview_models import VideoInterview, VisualAnalysis
from .video_interview_serializers import (
    VideoInterviewSerializer, VideoInterviewCreateSerializer, 
    VisualAnalysisSerializer, VisualAnalysisCreateSerializer
)
from .rag import generate_text_fireworks

class VideoInterviewViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    queryset = VideoInterview.objects.all()
    serializer_class = VideoInterviewSerializer

    def get_queryset(self):
        return VideoInterview.objects.filter(user=self.request.user).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return VideoInterviewCreateSerializer
        return VideoInterviewSerializer

    def perform_create(self, serializer):
        interview_type = serializer.validated_data.get('interview_type', 'HR')
        topic = serializer.validated_data.get('topic', '')
        
        # Generate questions using AI
        prompt = f"Generate 3 interview questions for a {interview_type} interview."
        if topic:
            prompt += f" The topic is: {topic}."
        prompt += " Return ONLY a JSON list of strings, e.g. [\"Question 1\", \"Question 2\"]."
        
        try:
            response = generate_text_fireworks(prompt, system_prompt="You are an expert interviewer. Output valid JSON only.")
            # Simple cleanup to ensure we get a list
            import json
            start = response.find('[')
            end = response.rfind(']') + 1
            if start != -1 and end != -1:
                questions = json.loads(response[start:end])
            else:
                questions = ["Could not generate questions. Please describe yourself."]
        except Exception as e:
            print(f"Error generating questions: {e}")
            questions = ["Tell me about yourself.", "What are your strengths?", "Why do you want this job?"]

        serializer.save(user=self.request.user, questions=questions)

    @action(detail=True, methods=['post'], url_path='add-analysis')
    def add_analysis(self, request, pk=None):
        interview = self.get_object()
        serializer = VisualAnalysisCreateSerializer(data=request.data, many=True)
        if serializer.is_valid():
            serializer.save(interview=interview)
            
            # Calculate overall score based on latest analysis
            # This is a simple average for now
            analyses = VisualAnalysis.objects.filter(interview=interview)
            if analyses.exists():
                avg_smile = sum(a.smile_score for a in analyses) / analyses.count()
                avg_eye = sum(a.eye_contact_score for a in analyses) / analyses.count()
                avg_posture = sum(a.posture_score for a in analyses) / analyses.count()
                
                # Simple weighted score
                overall = (avg_smile * 0.3) + (avg_eye * 0.4) + (avg_posture * 0.3)
                interview.overall_score = int(overall * 100) # Convert to 0-100
                interview.save()

            return Response({'status': 'analysis added', 'overall_score': interview.overall_score})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], url_path='generate-feedback')
    def generate_feedback(self, request, pk=None):
        interview = self.get_object()
        analyses = VisualAnalysis.objects.filter(interview=interview)
        
        if not analyses.exists():
            return Response({'error': 'No analysis data found'}, status=status.HTTP_400_BAD_REQUEST)

        # Summarize data for AI
        avg_smile = sum(a.smile_score for a in analyses) / analyses.count()
        avg_eye = sum(a.eye_contact_score for a in analyses) / analyses.count()
        avg_posture = sum(a.posture_score for a in analyses) / analyses.count()
        avg_nervous = sum(a.nervousness_score for a in analyses) / analyses.count()
        
        prompt = f"""
        Analyze the following visual data from a mock video interview:
        - Average Smile Score: {avg_smile:.2f} (0-1)
        - Average Eye Contact: {avg_eye:.2f} (0-1)
        - Average Posture Score: {avg_posture:.2f} (0-1)
        - Average Nervousness: {avg_nervous:.2f} (0-1)
        
        Provide a concise, constructive feedback summary (max 3 sentences) for the candidate. Focus on body language and facial expressions.
        """
        
        feedback = generate_text_fireworks(prompt, system_prompt="You are an expert interview coach specializing in body language.")
        interview.feedback_summary = feedback
        interview.save()
        
        return Response({'feedback': feedback})
