"""
Study Agent State Definitions
TypedDict for LangGraph state management
"""

from typing import TypedDict, List, Dict, Optional, Literal, Any
from datetime import datetime


class StudyAgentState(TypedDict, total=False):
    """
    State for Study Agent LangGraph workflow

    This state is passed between nodes and maintains the context
    of the conversation and processing steps.
    """

    # Input
    user_message: str  # Original user message
    user_id: Optional[int]  # Student/User ID
    session_id: Optional[str]  # Conversation session ID

    # Intent Classification
    intent: Optional[Literal[
        "quiz_generation",
        "time_estimation",
        "schedule_planning",
        "question_answering",
        "content_summary",
        "general_chat",
        "file_upload"
    ]]
    confidence: Optional[float]  # Intent classification confidence (0-1)

    # Context
    uploaded_files: Optional[List[Dict[str, Any]]]  # Uploaded study materials
    extracted_text: Optional[str]  # Text extracted from files
    context: Optional[str]  # Additional context for the query
    student_data: Optional[Dict[str, Any]]  # Student profile data

    # Processing State
    current_step: Optional[str]  # Current processing step
    processed_content: Optional[str]  # Processed/cleaned content

    # Quiz Generation
    quiz_topic: Optional[str]
    quiz_type: Optional[str]  # "повеќекратен избор", "вистина/неточно", etc.
    quiz_difficulty: Optional[str]  # "лесна", "средна", "тешка"
    num_questions: Optional[int]
    generated_quiz: Optional[Dict[str, Any]]  # Generated quiz data

    # Time Estimation
    task_description: Optional[str]
    estimated_hours: Optional[float]
    time_breakdown: Optional[Dict[str, float]]
    confidence_level: Optional[str]

    # Schedule Planning
    tasks: Optional[List[Dict[str, Any]]]
    available_hours: Optional[float]
    schedule: Optional[Dict[str, Any]]

    # Question Answering
    question: Optional[str]
    answer: Optional[str]
    sources: Optional[List[str]]

    # Content Summary
    summary: Optional[str]
    key_concepts: Optional[List[str]]
    study_tips: Optional[List[str]]

    # Output
    response: Optional[str]  # Final response to user
    response_type: Optional[str]  # Type of response (text, quiz, schedule, etc.)
    metadata: Optional[Dict[str, Any]]  # Additional metadata

    # Error Handling
    error: Optional[str]  # Error message if any
    error_type: Optional[str]  # Type of error

    # Routing
    next_node: Optional[str]  # Next node to route to
    should_end: bool  # Whether to end the graph execution

    # Logging
    timestamp: Optional[str]  # ISO timestamp
    processing_time: Optional[float]  # Processing time in seconds
    steps_taken: Optional[List[str]]  # List of nodes visited


class QuizQuestion(TypedDict):
    """Structure for a quiz question"""
    question_text: str
    question_type: str
    correct_answer: str
    options: Optional[Dict[str, str]]  # For multiple choice: {"А": "...", "Б": "..."}
    explanation: str
    difficulty: Optional[str]


class GeneratedQuiz(TypedDict):
    """Structure for a generated quiz"""
    questions: List[QuizQuestion]
    topic: str
    difficulty: str
    total_questions: int
    estimated_time_minutes: Optional[int]
    created_at: Optional[str]


class TaskEstimation(TypedDict):
    """Structure for task time estimation"""
    estimated_hours: float
    confidence_percentage: int
    time_breakdown: Dict[str, float]
    difficulty_level: str
    key_factors: List[str]
    recommended_strategy: str
    potential_challenges: List[str]


class ScheduleSession(TypedDict):
    """Structure for a scheduled study session"""
    task: str
    start_time: str
    duration_hours: float
    priority: str
    notes: Optional[str]


class StudySchedule(TypedDict):
    """Structure for a study schedule"""
    sessions: List[ScheduleSession]
    total_scheduled_hours: float
    feasibility_score: int  # 0-100
    recommendations: List[str]
    conflicts: Optional[List[Dict[str, Any]]]


# Helper function to create initial state
def create_initial_state(
    user_message: str,
    user_id: Optional[int] = None,
    session_id: Optional[str] = None
) -> StudyAgentState:
    """
    Create initial state for Study Agent

    Args:
        user_message: User's input message
        user_id: Optional user/student ID
        session_id: Optional session identifier

    Returns:
        Initial StudyAgentState
    """
    return StudyAgentState(
        user_message=user_message,
        user_id=user_id,
        session_id=session_id,
        should_end=False,
        timestamp=datetime.now().isoformat(),
        steps_taken=[],
        metadata={}
    )

