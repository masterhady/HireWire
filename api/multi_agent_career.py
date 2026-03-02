"""
Multi-Agent Career Development System
Specialized agents that work together to provide comprehensive career guidance
"""
import json
import re
import logging
from typing import Dict, List, Any, Optional
from decouple import config
import requests

from .supabase_views import search_maharatech_courses
from .rag import search_similar_jobs, embed_text

logger = logging.getLogger(__name__)

FIREWORKS_API_KEY = config("FIREWORKS_API_KEY", default=None)
FIREWORKS_BASE_URL = config("FIREWORKS_BASE_URL", default="https://api.fireworks.ai/inference/v1")
FIREWORKS_CHAT_MODEL = config("FIREWORKS_CHAT_MODEL", default="accounts/fireworks/models/llama-v3p3-70b-instruct")


def _call_fireworks_llm(system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
    """Helper to call Fireworks AI LLM"""
    if not FIREWORKS_API_KEY:
        raise ValueError("FIREWORKS_API_KEY is not configured")
    
    try:
        url = f"{FIREWORKS_BASE_URL}/chat/completions"
        headers = {
            "Authorization": f"Bearer {FIREWORKS_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": FIREWORKS_CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        }
        r = requests.post(url, headers=headers, json=payload, timeout=120)  # Increased timeout
        if not r.ok:
            error_text = r.text[:500]  # Limit error text
            raise Exception(f"Fireworks API error ({r.status_code}): {error_text}")
        
        response_data = r.json()
        if "choices" not in response_data or not response_data["choices"]:
            raise Exception("Invalid response format from Fireworks API")
        
        return response_data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    except requests.exceptions.Timeout:
        raise Exception("Request to Fireworks API timed out")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Network error calling Fireworks API: {str(e)}")
    except Exception as e:
        raise Exception(f"Error calling Fireworks API: {str(e)}")


def _parse_json_response(content: str) -> Dict[str, Any]:
    """Parse JSON from LLM response"""
    try:
        return json.loads(content)
    except Exception:
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except Exception:
                pass
    return {}


class CVAnalyzerAgent:
    """Agent specialized in analyzing CV structure and content"""
    
    def analyze(self, cv_text: str) -> Dict[str, Any]:
        """Analyze CV and return structured assessment"""
        if not cv_text or len(cv_text.strip()) < 10:
            return {"error": "CV text is too short or empty"}
        
        system_prompt = (
            "You are an expert CV/resume analyzer. Analyze the CV and return ONLY valid JSON with: "
            "current_role (string), experience_years (number), key_skills (array of strings), "
            "strengths (array of strings), weaknesses (array of strings), ats_score (number 0-100), "
            "overall_assessment (string), "
            "suggested_target_role (string: the next logical career step based on current role and experience, "
            "e.g., if current is 'Frontend Developer' suggest 'Senior Frontend Developer' or 'Full Stack Developer')."
        )
        user_prompt = f"CV Text:\n{cv_text[:5000]}\n\nProvide comprehensive CV analysis in JSON format. Based on the current position and experience, suggest the next logical target role for career advancement."
        
        try:
            content = _call_fireworks_llm(system_prompt, user_prompt, temperature=0.3)
            if not content:
                return {"error": "No response from AI model"}
            result = _parse_json_response(content)
            if not result:
                return {"error": "Failed to parse AI response"}
            return result
        except Exception as e:
            return {"error": f"CV Analysis error: {str(e)}"}


class SkillsGapAgent:
    """Agent specialized in identifying skills gaps for target roles"""
    
    def identify_gaps(self, cv_text: str, current_skills: List[str], target_role: Optional[str] = None) -> Dict[str, Any]:
        """Identify skills gaps for target role"""
        if not cv_text or len(cv_text.strip()) < 10:
            return {"error": "CV text is too short or empty", "missing_skills": []}
        
        role_context = f" for the role: {target_role}" if target_role else ""
        
        system_prompt = (
            "You are a skills gap analysis expert. Analyze the CV and identify missing skills "
            f"{role_context}. Return ONLY valid JSON with: "
            "missing_skills (array of strings), priority_skills (array of objects with skill, priority: high/medium/low), "
            "skill_importance (object mapping skill to importance level)."
        )
        user_prompt = (
            f"CV Text:\n{cv_text[:5000]}\n\n"
            f"Current Skills: {', '.join(current_skills[:20])}\n\n"
            f"Target Role: {target_role or 'General career advancement'}\n\n"
            "Identify skills gaps in JSON format."
        )
        
        try:
            content = _call_fireworks_llm(system_prompt, user_prompt, temperature=0.3)
            if not content:
                return {"error": "No response from AI model", "missing_skills": []}
            result = _parse_json_response(content)
            if not result:
                return {"error": "Failed to parse AI response", "missing_skills": []}
            return result
        except Exception as e:
            return {"error": f"Skills Gap Analysis error: {str(e)}", "missing_skills": []}


class MarketResearchAgent:
    """Agent specialized in market research and job trends"""
    
    def research(self, role: str, skills: List[str]) -> Dict[str, Any]:
        """Research market demand, salaries, and trends for role"""
        if not role:
            return {"error": "Role is required for market research"}
        
        system_prompt = (
            "You are a job market research expert. Provide market insights. Return ONLY valid JSON with: "
            "demand_level (string: high/medium/low), salary_range (string), "
            "market_trend (string), required_skills (array of strings), growth_outlook (string), "
            "competition_level (string: high/medium/low)."
        )
        user_prompt = (
            f"Research the job market for: {role}\n"
            f"Key skills: {', '.join(skills[:15])}\n\n"
            "Provide comprehensive market research in JSON format."
        )
        
        try:
            content = _call_fireworks_llm(system_prompt, user_prompt, temperature=0.3)
            if not content:
                return {"error": "No response from AI model"}
            result = _parse_json_response(content)
            if not result:
                return {"error": "Failed to parse AI response"}
            return result
        except Exception as e:
            return {"error": f"Market Research error: {str(e)}"}


class LearningPathAgent:
    """Agent specialized in finding learning resources and creating learning paths"""
    
    def find_resources(self, skills: List[str]) -> Dict[str, Any]:
        """Find learning resources for skills"""
        # Search for MaharaTech courses
        skill_courses = []
        for skill in skills[:5]:  # Limit to top 5 skills
            courses = search_maharatech_courses(skill, max_results=3)
            if courses:
                skill_courses.append({
                    "skill": skill,
                    "courses": courses
                })
        
        # Get AI recommendations for learning path
        ai_recommendations = {}
        if skills:
            try:
                system_prompt = (
                    "You are a learning path expert. Suggest learning resources and order. Return ONLY valid JSON with: "
                    "learning_path (array of objects with skill, resources array, estimated_time in weeks), "
                    "recommended_order (array of skill names in learning order), total_estimated_time (number in weeks)."
                )
                user_prompt = (
                    f"Skills to learn: {', '.join(skills[:10])}\n\n"
                    "Suggest a comprehensive learning path in JSON format."
                )
                
                content = _call_fireworks_llm(system_prompt, user_prompt, temperature=0.3)
                if content:
                    ai_recommendations = _parse_json_response(content)
            except Exception as e:
                ai_recommendations = {"error": f"Learning path AI recommendations failed: {str(e)}"}
        
        return {
            "skill_courses": skill_courses,
            "ai_recommendations": ai_recommendations
        }


class CareerPathPlannerAgent:
    """Agent specialized in planning career trajectories"""
    
    def plan_paths(self, cv_analysis: Dict, skills_gap: Dict, market_research: Dict) -> Dict[str, Any]:
        """Plan career paths based on analysis"""
        system_prompt = (
            "You are a career path planning expert. Create career trajectories. Return ONLY valid JSON with: "
            "career_paths (array of objects with title, description, transition_difficulty: easy/medium/hard, "
            "growth_potential: high/medium/low, timeline (string like '6-12 months'), required_steps (array of strings), success_probability (number 0-100)). "
            "Always return at least 3 career paths. Make sure career_paths is always an array."
        )
        
        # Limit data size to avoid token limits and handle missing/error data gracefully
        cv_summary = {
            "current_role": cv_analysis.get("current_role") if not cv_analysis.get("error") else "Software Professional",
            "experience_years": cv_analysis.get("experience_years", 0) if not cv_analysis.get("error") else 0,
            "key_skills": (cv_analysis.get("key_skills", [])[:10] if isinstance(cv_analysis.get("key_skills"), list) else []) if not cv_analysis.get("error") else []
        }
        if not cv_summary["current_role"] or cv_summary["current_role"] == "Unknown":
            cv_summary["current_role"] = "Software Professional"
        
        skills_summary = {
            "missing_skills": (skills_gap.get("missing_skills", [])[:10] if isinstance(skills_gap.get("missing_skills"), list) else []) if not skills_gap.get("error") else [],
            "priority_skills": (skills_gap.get("priority_skills", [])[:5] if isinstance(skills_gap.get("priority_skills"), list) else []) if not skills_gap.get("error") else []
        }
        
        market_summary = {
            "demand_level": market_research.get("demand_level") if not market_research.get("error") else "medium",
            "salary_range": market_research.get("salary_range") if not market_research.get("error") else "Competitive",
            "growth_outlook": market_research.get("growth_outlook") if not market_research.get("error") else "Positive"
        }
        
        user_prompt = (
            f"CV Analysis: {json.dumps(cv_summary, indent=2)}\n\n"
            f"Skills Gaps: {json.dumps(skills_summary, indent=2)}\n\n"
            f"Market Research: {json.dumps(market_summary, indent=2)}\n\n"
            "Suggest 3-5 detailed career paths based on this analysis. Each path should have: title, description, transition_difficulty, growth_potential, timeline, required_steps (array), and success_probability. Return ONLY valid JSON."
        )
        
        try:
            content = _call_fireworks_llm(system_prompt, user_prompt, temperature=0.4)
            if not content:
                return self._generate_fallback_paths(cv_summary)
            
            result = _parse_json_response(content)
            if not result or "career_paths" not in result:
                return self._generate_fallback_paths(cv_summary)
            
            # Ensure career_paths is a list
            if not isinstance(result.get("career_paths"), list):
                return self._generate_fallback_paths(cv_summary)
            
            # Validate that we have at least some paths
            if len(result.get("career_paths", [])) == 0:
                return self._generate_fallback_paths(cv_summary)
            
            return result
        except Exception as e:
            logger.warning(f"Career Path Planning AI call failed: {e}. Using fallback paths.")
            return self._generate_fallback_paths(cv_summary)
    
    def _generate_fallback_paths(self, cv_summary: Dict) -> Dict[str, Any]:
        """Generate basic career paths when AI call fails"""
        current_role = cv_summary.get("current_role", "Software Professional")
        if not current_role or current_role == "Unknown":
            current_role = "Software Professional"
        experience = cv_summary.get("experience_years", 0)
        if not isinstance(experience, (int, float)):
            experience = 0
        
        # Generate logical career paths based on current role
        fallback_paths = []
        
        # Path 1: Senior/Lead level
        if "senior" not in current_role.lower() and "lead" not in current_role.lower():
            if "developer" in current_role.lower():
                fallback_paths.append({
                    "title": f"Senior {current_role}",
                    "description": f"Advance to senior level with {current_role} expertise, focusing on technical leadership and mentoring.",
                    "transition_difficulty": "medium",
                    "growth_potential": "high",
                    "timeline": "12-18 months",
                    "required_steps": [
                        "Deepen technical expertise in current role",
                        "Take on leadership responsibilities",
                        "Mentor junior team members",
                        "Complete advanced certifications"
                    ],
                    "success_probability": 75
                })
            
            # Path 2: Full Stack (if frontend/backend)
            if "frontend" in current_role.lower():
                fallback_paths.append({
                    "title": "Full Stack Developer",
                    "description": "Expand to full stack development by learning backend technologies and database design.",
                    "transition_difficulty": "medium",
                    "growth_potential": "high",
                    "timeline": "12-24 months",
                    "required_steps": [
                        "Learn backend frameworks (Node.js, Python, etc.)",
                        "Master database design and SQL",
                        "Build full-stack projects",
                        "Understand DevOps basics"
                    ],
                    "success_probability": 70
                })
            elif "backend" in current_role.lower():
                fallback_paths.append({
                    "title": "Full Stack Developer",
                    "description": "Expand to full stack development by learning frontend technologies and UI/UX principles.",
                    "transition_difficulty": "medium",
                    "growth_potential": "high",
                    "timeline": "12-24 months",
                    "required_steps": [
                        "Learn modern frontend frameworks (React, Vue, etc.)",
                        "Master CSS and responsive design",
                        "Build full-stack projects",
                        "Understand user experience principles"
                    ],
                    "success_probability": 70
                })
            
            # Path 3: Technical Lead/Manager
            if experience >= 3:
                fallback_paths.append({
                    "title": "Technical Lead or Engineering Manager",
                    "description": "Transition to leadership role, managing teams and technical strategy.",
                    "transition_difficulty": "hard",
                    "growth_potential": "high",
                    "timeline": "18-36 months",
                    "required_steps": [
                        "Develop leadership and communication skills",
                        "Take on project management responsibilities",
                        "Learn team management practices",
                        "Complete leadership training"
                    ],
                    "success_probability": 60
                })
        else:
            # Already senior level
            fallback_paths.append({
                "title": "Principal Engineer or Tech Lead",
                "description": "Advance to principal level with architectural and strategic responsibilities.",
                "transition_difficulty": "hard",
                "growth_potential": "high",
                "timeline": "24-36 months",
                "required_steps": [
                    "Master system architecture and design",
                    "Lead major technical initiatives",
                    "Mentor senior engineers",
                    "Contribute to technical strategy"
                ],
                "success_probability": 65
            })
        
        # Always ensure we have at least 3 paths - add generic ones if needed
        generic_paths = [
            {
                "title": "Career Advancement in Current Field",
                "description": "Continue growing in your current field with focused skill development and experience building.",
                "transition_difficulty": "easy",
                "growth_potential": "medium",
                "timeline": "6-12 months",
                "required_steps": [
                    "Build a strong portfolio",
                    "Network with industry professionals",
                    "Stay updated with latest technologies",
                    "Seek challenging projects"
                ],
                "success_probability": 80
            },
            {
                "title": "Specialization Path",
                "description": "Deepen expertise in a specific technology or domain area.",
                "transition_difficulty": "medium",
                "growth_potential": "high",
                "timeline": "12-18 months",
                "required_steps": [
                    "Choose a specialization area",
                    "Complete advanced training",
                    "Work on specialized projects",
                    "Build expertise portfolio"
                ],
                "success_probability": 75
            },
            {
                "title": "Cross-Functional Growth",
                "description": "Expand skills across different areas to become more versatile.",
                "transition_difficulty": "medium",
                "growth_potential": "high",
                "timeline": "12-24 months",
                "required_steps": [
                    "Learn complementary skills",
                    "Work on diverse projects",
                    "Collaborate across teams",
                    "Build cross-functional experience"
                ],
                "success_probability": 70
            }
        ]
        
        # Add generic paths until we have at least 3
        while len(fallback_paths) < 3:
            fallback_paths.append(generic_paths[len(fallback_paths) % len(generic_paths)])
        
        return {"career_paths": fallback_paths[:5]}


class JobMatcherAgent:
    """Agent specialized in finding matching jobs using vector search"""
    
    def find_matching_jobs(self, cv_text: str, top_n: int = 5) -> Dict[str, Any]:
        """Find matching jobs using vector similarity"""
        try:
            # Get CV embedding
            cv_embedding = embed_text(cv_text)
            
            # Search for similar jobs
            similar_jobs = search_similar_jobs(cv_embedding, top_n=top_n, similarity_threshold=0.6)
            
            matching_jobs = []
            for job in similar_jobs:
                if not job or len(job) < 6:
                    continue
                try:
                    # Tuple structure from search_similar_jobs: (id, title, description, requirements, company_id, score)
                    job_id = str(job[0]) if job[0] is not None else "unknown"
                    title = str(job[1]) if job[1] is not None else "Unknown Position"
                    # Score is at index 5, not 2
                    similarity_score = 0.0
                    if len(job) > 5 and job[5] is not None:
                        try:
                            similarity_score = float(job[5])
                        except (ValueError, TypeError):
                            # If score is not a valid number, default to 0.0
                            similarity_score = 0.0
                    
                    matching_jobs.append({
                        "job_id": job_id,
                        "title": title,
                        "similarity_score": similarity_score
                    })
                except Exception as job_error:
                    # Skip this job if there's an error processing it
                    logger.warning(f"Error processing job in JobMatcherAgent: {job_error}")
                    continue
            
            return {
                "matching_jobs": matching_jobs,
                "total_matches": len(matching_jobs)
            }
        except Exception as e:
            return {"error": str(e), "matching_jobs": []}


class MultiAgentCareerCoordinator:
    """Coordinates multiple agents to provide comprehensive career guidance"""
    
    def __init__(self):
        self.cv_analyzer = CVAnalyzerAgent()
        self.skills_gap = SkillsGapAgent()
        self.market_research = MarketResearchAgent()
        self.learning_path = LearningPathAgent()
        self.career_planner = CareerPathPlannerAgent()
        self.job_matcher = JobMatcherAgent()
    
    def analyze_career(self, cv_text: str, target_role: Optional[str] = None) -> Dict[str, Any]:
        """
        Coordinate all agents to provide comprehensive career analysis
        
        Returns:
            {
                "agents_status": {...},
                "cv_analysis": {...},
                "skills_gap": {...},
                "market_research": {...},
                "learning_path": {...},
                "career_paths": {...},
                "job_matches": {...},
                "synthesis": {...}
            }
        """
        results = {
            "agents_status": {},
            "cv_analysis": {},
            "skills_gap": {},
            "market_research": {},
            "learning_path": {},
            "career_paths": {},
            "job_matches": {},
            "synthesis": {}
        }
        
        try:
            # Step 1: CV Analysis
            try:
                results["agents_status"]["cv_analyzer"] = "running"
                cv_analysis = self.cv_analyzer.analyze(cv_text)
                if not cv_analysis or "error" in cv_analysis:
                    raise Exception(f"CV Analysis failed: {cv_analysis.get('error', 'Unknown error')}")
                results["cv_analysis"] = cv_analysis
                results["agents_status"]["cv_analyzer"] = "completed"
            except Exception as e:
                results["agents_status"]["cv_analyzer"] = f"failed: {str(e)}"
                results["cv_analysis"] = {"error": str(e)}
                # Use defaults to continue
                cv_analysis = {"key_skills": [], "current_role": "Unknown"}
            
            current_skills = cv_analysis.get("key_skills", [])
            current_role = cv_analysis.get("current_role", "Software Developer")
            
            # Auto-infer target role from CV if not provided
            if not target_role:
                # Use suggested target role from CV analysis, or infer from current role
                target_role = cv_analysis.get("suggested_target_role")
                if not target_role and current_role:
                    # Fallback: add "Senior" prefix or infer logical next step
                    if "senior" not in current_role.lower() and "lead" not in current_role.lower():
                        # For junior/mid-level, suggest senior version or logical advancement
                        if current_role.lower().startswith(("junior", "jr")):
                            target_role = current_role.replace("Junior", "Senior").replace("Jr", "Senior").replace("junior", "Senior").replace("jr", "Senior").strip()
                        elif "developer" in current_role.lower():
                            if "frontend" in current_role.lower():
                                target_role = "Full Stack Developer or Senior Frontend Developer"
                            elif "backend" in current_role.lower():
                                target_role = "Senior Backend Developer or Full Stack Developer"
                            else:
                                target_role = f"Senior {current_role}"
                        else:
                            target_role = f"Senior {current_role}"
                    else:
                        # Already senior, suggest management or specialization
                        if "developer" in current_role.lower():
                            target_role = "Tech Lead or Engineering Manager"
                        else:
                            target_role = f"Lead {current_role}" if "Lead" not in current_role else f"Principal {current_role}"
                
                # Store inferred target role in results
                results["inferred_target_role"] = target_role
            
            # Step 2: Skills Gap Analysis
            try:
                results["agents_status"]["skills_gap"] = "running"
                skills_gap = self.skills_gap.identify_gaps(cv_text, current_skills, target_role)
                if not skills_gap or "error" in skills_gap:
                    raise Exception(f"Skills Gap Analysis failed: {skills_gap.get('error', 'Unknown error')}")
                results["skills_gap"] = skills_gap
                results["agents_status"]["skills_gap"] = "completed"
            except Exception as e:
                results["agents_status"]["skills_gap"] = f"failed: {str(e)}"
                results["skills_gap"] = {"error": str(e), "missing_skills": []}
                skills_gap = results["skills_gap"]
            
            # Step 3: Market Research
            try:
                results["agents_status"]["market_research"] = "running"
                missing_skills = skills_gap.get("missing_skills", [])[:3]
                research_role = target_role or current_role
                market_research = self.market_research.research(research_role, missing_skills + current_skills[:3])
                if not market_research or "error" in market_research:
                    raise Exception(f"Market Research failed: {market_research.get('error', 'Unknown error')}")
                results["market_research"] = market_research
                results["agents_status"]["market_research"] = "completed"
            except Exception as e:
                results["agents_status"]["market_research"] = f"failed: {str(e)}"
                results["market_research"] = {"error": str(e)}
                market_research = results["market_research"]
            
            # Step 4: Learning Path
            try:
                results["agents_status"]["learning_path"] = "running"
                missing_skills = skills_gap.get("missing_skills", [])[:5]
                learning_path = self.learning_path.find_resources(missing_skills)
                results["learning_path"] = learning_path
                results["agents_status"]["learning_path"] = "completed"
            except Exception as e:
                results["agents_status"]["learning_path"] = f"failed: {str(e)}"
                results["learning_path"] = {"error": str(e), "skill_courses": []}
                learning_path = results["learning_path"]
            
            # Step 5: Career Path Planning (make it resilient - always generate paths)
            try:
                results["agents_status"]["career_planner"] = "running"
                
                # Prepare CV summary for fallback (always available)
                cv_summary = {
                    "current_role": cv_analysis.get("current_role", "Software Professional") if not cv_analysis.get("error") else "Software Professional",
                    "experience_years": cv_analysis.get("experience_years", 0) if not cv_analysis.get("error") else 0
                }
                if not cv_summary["current_role"] or cv_summary["current_role"] == "Unknown":
                    cv_summary["current_role"] = current_role if current_role and current_role != "Unknown" else "Software Professional"
                
                # Try to get AI-generated paths
                try:
                    career_paths = self.career_planner.plan_paths(cv_analysis, skills_gap, market_research)
                except Exception as ai_error:
                    logger.warning(f"Career Path AI call failed: {ai_error}. Using fallback.", exc_info=True)
                    career_paths = None
                
                # Validate and ensure we have paths - use fallback if needed
                use_fallback = False
                if not career_paths:
                    use_fallback = True
                elif "career_paths" not in career_paths:
                    use_fallback = True
                elif not isinstance(career_paths.get("career_paths"), list):
                    use_fallback = True
                elif len(career_paths.get("career_paths", [])) == 0:
                    use_fallback = True
                
                if use_fallback:
                    logger.info(f"Using fallback career paths for role: {cv_summary['current_role']}")
                    career_paths = self.career_planner._generate_fallback_paths(cv_summary)
                    results["agents_status"]["career_planner"] = "completed_with_fallback"
                else:
                    results["agents_status"]["career_planner"] = "completed"
                
                # Final validation - MUST have paths by now
                if not career_paths or "career_paths" not in career_paths or not isinstance(career_paths.get("career_paths"), list) or len(career_paths.get("career_paths", [])) == 0:
                    logger.error(f"CRITICAL: Career paths still empty after all fallbacks! Generating minimal paths.")
                    # Emergency fallback - guaranteed paths
                    career_paths = {
                        "career_paths": [
                            {
                                "title": f"Senior {cv_summary['current_role']}",
                                "description": f"Advance to senior level in {cv_summary['current_role']} with technical leadership responsibilities.",
                                "transition_difficulty": "medium",
                                "growth_potential": "high",
                                "timeline": "12-18 months",
                                "required_steps": [
                                    "Deepen technical expertise",
                                    "Take on leadership responsibilities",
                                    "Mentor team members",
                                    "Complete relevant certifications"
                                ],
                                "success_probability": 75
                            },
                            {
                                "title": "Technical Lead or Manager",
                                "description": "Transition to leadership role managing teams and technical strategy.",
                                "transition_difficulty": "hard",
                                "growth_potential": "high",
                                "timeline": "18-36 months",
                                "required_steps": [
                                    "Develop leadership skills",
                                    "Manage technical projects",
                                    "Learn team management",
                                    "Complete leadership training"
                                ],
                                "success_probability": 65
                            },
                            {
                                "title": "Career Growth in Current Field",
                                "description": "Continue advancing through skill development and experience building.",
                                "transition_difficulty": "easy",
                                "growth_potential": "medium",
                                "timeline": "6-12 months",
                                "required_steps": [
                                    "Build strong portfolio",
                                    "Network with professionals",
                                    "Stay updated with technology",
                                    "Seek challenging projects"
                                ],
                                "success_probability": 80
                            }
                        ]
                    }
                    results["agents_status"]["career_planner"] = "completed_with_emergency_fallback"
                
                results["career_paths"] = career_paths
            except Exception as e:
                # Even if there's an exception, try to generate fallback paths
                logger.warning(f"Career Path Planning exception: {e}. Attempting fallback.", exc_info=True)
                try:
                    cv_summary = {
                        "current_role": current_role if current_role and current_role != "Unknown" else "Software Professional",
                        "experience_years": cv_analysis.get("experience_years", 0) if not cv_analysis.get("error") else 0
                    }
                    career_paths = self.career_planner._generate_fallback_paths(cv_summary)
                    results["career_paths"] = career_paths
                    results["agents_status"]["career_planner"] = "completed_with_fallback"
                except Exception as fallback_error:
                    logger.error(f"Fallback path generation also failed: {fallback_error}", exc_info=True)
                    # Last resort: use minimal generic paths
                    results["career_paths"] = {
                        "career_paths": [
                            {
                                "title": "Senior Software Developer",
                                "description": "Advance to senior level with technical leadership responsibilities.",
                                "transition_difficulty": "medium",
                                "growth_potential": "high",
                                "timeline": "12-18 months",
                                "required_steps": [
                                    "Deepen technical expertise",
                                    "Take on leadership responsibilities",
                                    "Mentor team members",
                                    "Complete certifications"
                                ],
                                "success_probability": 75
                            },
                            {
                                "title": "Technical Lead",
                                "description": "Transition to leadership role managing teams and projects.",
                                "transition_difficulty": "hard",
                                "growth_potential": "high",
                                "timeline": "18-36 months",
                                "required_steps": [
                                    "Develop leadership skills",
                                    "Manage technical projects",
                                    "Learn team management",
                                    "Complete leadership training"
                                ],
                                "success_probability": 65
                            },
                            {
                                "title": "Career Growth in Current Field",
                                "description": "Continue advancing through skill development and experience.",
                                "transition_difficulty": "easy",
                                "growth_potential": "medium",
                                "timeline": "6-12 months",
                                "required_steps": [
                                    "Build portfolio",
                                    "Network professionally",
                                    "Stay updated with technology",
                                    "Seek challenging projects"
                                ],
                                "success_probability": 80
                            }
                        ]
                    }
                    results["agents_status"]["career_planner"] = "completed_with_minimal_fallback"
            
            # ABSOLUTE FINAL SAFETY CHECK - ensure career_paths is ALWAYS set properly
            if "career_paths" not in results or not results["career_paths"]:
                logger.critical("CRITICAL: career_paths not set after all attempts! Setting emergency paths.")
                results["career_paths"] = {
                    "career_paths": [
                        {
                            "title": "Senior Software Developer",
                            "description": "Advance to senior level with technical leadership responsibilities.",
                            "transition_difficulty": "medium",
                            "growth_potential": "high",
                            "timeline": "12-18 months",
                            "required_steps": [
                                "Deepen technical expertise",
                                "Take on leadership responsibilities",
                                "Mentor team members",
                                "Complete certifications"
                            ],
                            "success_probability": 75
                        },
                        {
                            "title": "Technical Lead",
                            "description": "Transition to leadership role managing teams and projects.",
                            "transition_difficulty": "hard",
                            "growth_potential": "high",
                            "timeline": "18-36 months",
                            "required_steps": [
                                "Develop leadership skills",
                                "Manage technical projects",
                                "Learn team management",
                                "Complete leadership training"
                            ],
                            "success_probability": 65
                        },
                        {
                            "title": "Career Growth",
                            "description": "Continue advancing through skill development and experience.",
                            "transition_difficulty": "easy",
                            "growth_potential": "medium",
                            "timeline": "6-12 months",
                            "required_steps": [
                                "Build portfolio",
                                "Network professionally",
                                "Stay updated with technology",
                                "Seek challenging projects"
                            ],
                            "success_probability": 80
                        }
                    ]
                }
            elif not isinstance(results["career_paths"].get("career_paths"), list) or len(results["career_paths"].get("career_paths", [])) == 0:
                logger.critical("CRITICAL: career_paths is empty or invalid! Setting emergency paths.")
                results["career_paths"] = {
                    "career_paths": [
                        {
                            "title": "Senior Software Developer",
                            "description": "Advance to senior level with technical leadership responsibilities.",
                            "transition_difficulty": "medium",
                            "growth_potential": "high",
                            "timeline": "12-18 months",
                            "required_steps": [
                                "Deepen technical expertise",
                                "Take on leadership responsibilities",
                                "Mentor team members",
                                "Complete certifications"
                            ],
                            "success_probability": 75
                        }
                    ]
                }
            
            # Ensure career_paths variable is set for synthesis
            career_paths = results.get("career_paths", {"career_paths": []})
            
            # Step 6: Job Matching (non-critical, can fail silently)
            try:
                results["agents_status"]["job_matcher"] = "running"
                job_matches = self.job_matcher.find_matching_jobs(cv_text, top_n=5)
                results["job_matches"] = job_matches
                results["agents_status"]["job_matcher"] = "completed"
            except Exception as e:
                results["agents_status"]["job_matcher"] = f"failed: {str(e)}"
                results["job_matches"] = {"error": str(e), "matching_jobs": []}
                job_matches = results["job_matches"]
            
            # Step 7: Synthesis
            try:
                results["agents_status"]["synthesis"] = "running"
                synthesis = self._synthesize_results(cv_analysis, skills_gap, market_research, learning_path, career_paths, job_matches)
                if not synthesis or "error" in synthesis:
                    # Create a basic synthesis if AI synthesis fails
                    synthesis = {
                        "executive_summary": "Career analysis completed with some limitations. Please review individual agent results.",
                        "top_recommendations": [],
                        "priority_actions": [],
                        "confidence_score": 70
                    }
                results["synthesis"] = synthesis
                results["agents_status"]["synthesis"] = "completed"
            except Exception as e:
                results["agents_status"]["synthesis"] = f"failed: {str(e)}"
                results["synthesis"] = {
                    "error": str(e),
                    "executive_summary": "Synthesis step encountered an error. Please review individual agent results.",
                    "top_recommendations": [],
                    "priority_actions": []
                }
            
            results["agents_status"]["all"] = "completed"
            
        except Exception as e:
            results["error"] = str(e)
            results["agents_status"]["error"] = str(e)
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Multi-agent career analysis failed: {e}", exc_info=True)
        
        return results
    
    def _synthesize_results(self, cv_analysis: Dict, skills_gap: Dict, 
                          market_research: Dict, learning_path: Dict, 
                          career_paths: Dict, job_matches: Dict) -> Dict[str, Any]:
        """Synthesize all agent results into actionable recommendations"""
        system_prompt = (
            "You are a career advisor synthesizing multiple analyses. Return ONLY valid JSON with: "
            "executive_summary (string), top_recommendations (array of strings), "
            "priority_actions (array of objects with action, priority: high/medium/low, timeline in weeks), "
            "confidence_score (number 0-100), next_30_days_plan (array of specific actions)."
        )
        
        # Create summaries to avoid token limits
        cv_summary = {
            "current_role": cv_analysis.get("current_role", "Unknown"),
            "key_skills": cv_analysis.get("key_skills", [])[:10],
            "strengths": cv_analysis.get("strengths", [])[:5]
        }
        skills_summary = {
            "missing_skills": skills_gap.get("missing_skills", [])[:10]
        }
        market_summary = {
            "demand_level": market_research.get("demand_level", "unknown"),
            "salary_range": market_research.get("salary_range", "Unknown")
        }
        paths_summary = {
            "career_paths": career_paths.get("career_paths", [])[:3] if isinstance(career_paths.get("career_paths"), list) else []
        }
        jobs_summary = {
            "total_matches": job_matches.get("total_matches", 0)
        }
        
        user_prompt = (
            f"CV Analysis: {json.dumps(cv_summary, indent=2)}\n\n"
            f"Skills Gap: {json.dumps(skills_summary, indent=2)}\n\n"
            f"Market Research: {json.dumps(market_summary, indent=2)}\n\n"
            f"Career Paths: {json.dumps(paths_summary, indent=2)}\n\n"
            f"Job Matches: {json.dumps(jobs_summary, indent=2)}\n\n"
            "Synthesize into actionable, prioritized recommendations in JSON format."
        )
        
        try:
            content = _call_fireworks_llm(system_prompt, user_prompt, temperature=0.3)
            if not content:
                return {
                    "executive_summary": "Analysis completed. Please review individual agent results for details.",
                    "top_recommendations": [],
                    "priority_actions": [],
                    "confidence_score": 70
                }
            result = _parse_json_response(content)
            if not result:
                return {
                    "executive_summary": "Analysis completed. Please review individual agent results for details.",
                    "top_recommendations": [],
                    "priority_actions": [],
                    "confidence_score": 70
                }
            return result
        except Exception as e:
            return {
                "error": f"Synthesis error: {str(e)}",
                "executive_summary": "Analysis completed with some limitations. Please review individual agent results.",
                "top_recommendations": [],
                "priority_actions": [],
                "confidence_score": 60
            }
