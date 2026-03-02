import logging
import json
from api.rag import generate_text_fireworks

logger = logging.getLogger(__name__)

class CodingProfileAnalysisService:
    @staticmethod
    def analyze_profile(profile):
        """
        Generates an AI analysis of the user's coding profile stats.
        """
        stats = profile.stats
        platform = profile.platform
        
        if not stats:
            return None

        prompt = f"""
        You are an expert technical interviewer and career coach.
        Analyze the following {platform} statistics for a job seeker:
        
        {json.dumps(stats, indent=2)}
        
        The stats include advanced metrics like:
        - Weighted Acceptance Rate (accounts for problem difficulty)
        - Consistency (streaks, weekly average)
        - Problem Solving Score (0-100 unified score)
        - Community Engagement
        
        Provide a constructive analysis in JSON format with the following keys:
        - "summary": A brief 1-2 sentence summary of their skill level.
        - "strengths": A list of 2-3 key strengths based on the data.
        - "weaknesses": A list of 2-3 areas for improvement.
        - "recommendations": A list of 2-3 specific actions to take next (e.g., "Practice dynamic programming", "Participate in more contests").
        - "estimated_level": One of "Beginner", "Intermediate", "Advanced", "Expert".
        - "insights": A list of 2-3 short, punchy insights (e.g., "Strong consistency with moderate difficulty", "High volume but low acceptance rate").
        
        Do not include any markdown formatting or explanations outside the JSON.
        """

        try:
            # Using the existing generate_text_fireworks function from rag.py
            # We might need to adjust if it returns markdown code blocks
            response_text = generate_text_fireworks(prompt, system_prompt="You are a helpful JSON-speaking assistant.")
            
            # Clean up potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
                
            analysis = json.loads(response_text)
            return analysis

        except Exception as e:
            logger.error(f"Error generating analysis for profile {profile.id}: {str(e)}")
            return None
