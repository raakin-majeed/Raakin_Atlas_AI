import json
from typing import Dict, Any, List
from app.services.ai.gemini import gemini_client

class StudentAIService:
    """Service for generating AI-driven feedback and recovery plans for students."""

    STUDENT_INSIGHT_PROMPT = """Analyze the following student academic performance metrics and provide a constructive, supportive explanation tailored for the student.

Student Data:
- Average Score: {average_score}
- Weak Subjects: {weak_subjects}
- Academic Risk Assessment: {risk_level}
- Attendance Rate: {attendance}%
- Additional Observations: {flags}

Task:
1. Summarize the student's current academic standing (summary).
2. Explain to the student what the '{risk_level}' risk level means in simple, encouraging language (risk_explanation).
3. Suggest 3 to 5 realistic, actionable steps for academic recovery and improvement (recovery_plan).
4. Provide a supportive motivational closing (motivation).

Response format MUST be strictly JSON:
{{
  "summary": "string explaining position",
  "risk_explanation": "string explaining risk simply",
  "recovery_plan": ["step 1", "step 2", "step 3"],
  "motivation": "supportive message"
}}

Respond with ONLY the JSON object, no introductory text or markdown code blocks."""

    async def generate_student_insight(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Uses Gemini to generate personalized academic insights and recovery steps for a student.
        
        Args:
            analysis (Dict[str, Any]): Analysis results containing metrics like:
                average_score, weak_subjects, risk_level, attendance, and optional flags.
                
        Returns:
            Dict[str, Any]: Structured AI response containing summary, risk explanation,
                recovery plan, and motivational message.
        """
        if not gemini_client.is_available():
            return self._get_demo_insight(analysis)

        # Extract values with safe defaults
        weak_subs_list = analysis.get("weak_subjects", [])
        weak_subs = ", ".join(weak_subs_list) if weak_subs_list else "None"
        
        risk = analysis.get("risk_level", "Medium")
        attendance = analysis.get("attendance", 0.0)
        
        flags_list = analysis.get("flags", [])
        flags = ", ".join(flags_list) if flags_list else "None"

        prompt = self.STUDENT_INSIGHT_PROMPT.format(
            average_score=analysis.get("average_score", 0.0),
            weak_subjects=weak_subs,
            risk_level=risk,
            attendance=attendance,
            flags=flags
        )

        try:
            # Attempt to use the Gemini client (using generate_text as currently available in gemini.py)
            response = await gemini_client.generate_text(
                prompt=prompt,
                temperature=0.3,
            )
            
            # Handle Gemini response: Extract text using .text if it's a response object, 
            # otherwise treat as raw text (as currently returned by generate_text)
            raw_content = response.text if hasattr(response, "text") else response
            clean_text = raw_content.strip()
            
            # Remove possible markdown formatting from AI output
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.startswith("```"):
                clean_text = clean_text[3:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            # Improve JSON parsing safety
            try:
                return json.loads(clean_text)
            except (json.JSONDecodeError, ValueError):
                print(f"Failed to parse AI response as JSON: {clean_text[:100]}...")
                return self._get_demo_insight(analysis)
            
        except Exception as e:
            # Fallback for API errors or other infrastructure issues
            print(f"Error in StudentAIService: {e}")
            return self._get_demo_insight(analysis)

    def _get_demo_insight(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a static fallback response when AI is unavailable."""
        risk = analysis.get("risk_level", "Medium")
        weak_subjects = analysis.get("weak_subjects", [])
        
        recovery_plan = [
            "Schedule consistent study blocks for your weaker subjects.",
            "Attend extra tutoring or peer-study groups if available.",
            "Ensure your attendance stays above 75% for better engagement."
        ]
        
        if weak_subjects:
            recovery_plan.insert(0, f"Focus intensely on {', '.join(weak_subjects)} fundamentals.")
            
        return {
            "summary": f"Your current metrics show an average of {analysis.get('average_score', 0)}% with some specific areas needing attention.",
            "risk_explanation": f"A '{risk}' risk level indicates that while you have strengths, there's a possibility of falling behind if certain adjustments aren't made soon.",
            "recovery_plan": recovery_plan[:5],
            "motivation": "You have the potential to turn this around. Small, consistent improvements lead to great success!"
        }

# Global service instance
student_ai_service = StudentAIService()
