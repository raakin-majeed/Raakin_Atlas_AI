from typing import Dict, List, Any

class StudentAnalysisService:
    """Service for analyzing student performance and predicting academic risk levels."""

    def analyze_student_performance(self, attendance: float, subject_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Processes student attendance and grades to provide a risk analysis.
        
        Args:
            attendance (float): Current attendance percentage (0-100).
            subject_scores (Dict[str, float]): Dictionary of subject names and their scores.
            
        Returns:
            Dict[str, Any]: An analysis report containing average score, weak subjects, and risk level.
        """
        if not subject_scores:
            return {
                "average_score": 0.0,
                "weak_subjects": [],
                "risk_level": "High" if attendance < 60 else "Medium",
                "attendance": attendance,
                "message": "No subject scores provided for analysis."
            }

        # Calculate average score
        scores = list(subject_scores.values())
        average_score = sum(scores) / len(scores)

        # Identify weak subjects (score < 50)
        weak_subjects = [subject for subject, score in subject_scores.items() if score < 50]

        # Determine risk_level based on performance and attendance metrics
        # Risk Levels:
        # High: Average < 50 OR Attendance < 60 OR 3+ weak subjects
        # Medium: Average < 70 OR Attendance < 75 OR 1+ weak subjects
        # Low: Excellent performance (Avg >= 70 AND Attendance >= 75 AND 0 weak subjects)
        
        if average_score < 50 or attendance < 60 or len(weak_subjects) >= 3:
            risk_level = "High"
        elif average_score < 70 or attendance < 75 or len(weak_subjects) > 0:
            risk_level = "Medium"
        else:
            risk_level = "Low"

        return {
            "average_score": round(average_score, 2),
            "weak_subjects": weak_subjects,
            "risk_level": risk_level,
            "attendance": attendance,
            "subject_count": len(subject_scores)
        }

# Instantiate service for project-wide use
student_analysis_service = StudentAnalysisService()
