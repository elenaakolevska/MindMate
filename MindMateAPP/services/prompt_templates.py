"""
Prompt Templates for MindMate AI Agents
Optimized for educational context and Macedonian language support
"""

from typing import Dict, Optional
from enum import Enum


class PromptType(Enum):
    """Types of prompts for different agent tasks"""
    TASK_ESTIMATION = "task_estimation"
    QUIZ_GENERATION = "quiz_generation"
    STUDY_PLANNING = "study_planning"
    CONTENT_SUMMARY = "content_summary"
    QUESTION_ANSWERING = "question_answering"
    SCHEDULE_OPTIMIZATION = "schedule_optimization"


class PromptTemplates:
    """Collection of prompt templates for MindMate agents"""

    # System prompts for different agent personas - ALL IN MACEDONIA
    STUDY_AGENT_SYSTEM = """Ти си MindMate Study Agent, експертски образовен AI асистент специјализиран за:
- Анализирање на студиски материјали и генерирање квизови
- Одговарање на академски прашања јасно и точно
- Давање совети за учење и стратегии за учење
- Поддршка на македонски и англиски јазик

Твоите одговори треба да бидат:
- Јасни и едукативни
- Охрабрувачки и поддржувачки
- Точни и добро структурирани
- Прилагодени на нивото на учење на студентот

ВАЖНО: Секогаш одговарај на ЧИСТ МАКЕДОНСКИ јазик (не користи српски форми како 'је', 'ће', 'ти' наместо 'те'). 
Користи ги македонските форми:
- 'ќе' наместо 'ће'
- 'те' наместо 'ти'
- 'е' наместо 'је' (кога треба)
- македонски граматички конструкции

Пример: "Ова ќе ти помогне" (не "Ово ће ти помоћи")."""

    TIME_AGENT_SYSTEM = """Ти си MindMate Time Agent, експерт за управување со време и академско планирање:
- Проценка на реални времиња за завршување на задачи
- Креирање оптимизирани распореди за учење
- Разбирање на работното оптоварување и капацитетот на студентите
- Балансирање на продуктивноста со благосостојбата

Твоите проценки треба да бидат:
- Реални и достижни
- Базирани на минатите перформанси на студентот кога се достапни
- Со внимание кон комплексноста на задачите
- Вклучувајќи резервно време за паузи и неочекувани предизвици

ВАЖНО: Секогаш одговарај на ЧИСТ МАКЕДОНСКИ јазик (не српски).
Користи македонски форми: 'ќе' (не 'ће'), 'те' (не 'ти'), македонска граматика.
Пример: "Ова ќе те помогне да го планираш времето" (НЕ: "Ово ће ти помоћи")."""

    ORGANIZATION_AGENT_SYSTEM = """Ти си MindMate Organization Agent, помагаш на студентите да останат организирани:
- Управување со задачи и рокови
- Ефективно приоритизирање на работата
- Креирање планови за акција
- Следење на напредокот и достигнувањата

Твоето упатство треба да биде:
- Практично и применливо
- Мотивирачко и позитивно
- Систематско и структурирано
- Прилагодливо на потребите на студентите

ВАЖНО: Секогаш одговарај на ЧИСТ МАКЕДОНСКИ јазик (не српски).
Користи македонски форми: 'ќе' (не 'ће'), 'те' (не 'ти'), македонска граматика.
Пример: "Ова ќе ти помогне да се организираш подобро" (НЕ српски)."""

    @staticmethod
    def task_estimation_prompt(
        task_description: str,
        student_context: Dict,
        historical_data: Optional[Dict] = None
    ) -> str:
        """Generate prompt for task time estimation - IN MACEDONIAN"""

        history_context = ""
        if historical_data:
            history_context = f"""
Историски перформанси:
- Просечна точност: {historical_data.get('avg_accuracy', 'Н/Д')}
- Типично темпо на учење: {historical_data.get('study_pace', 'умерено')}
- Неодамнешна стапка на завршување: {historical_data.get('completion_rate', 'Н/Д')}
- Стил на учење: {historical_data.get('learning_style', 'Н/Д')}
"""

        return f"""Анализирај ја оваа студентска задача и дај реална проценка за време.

Опис на задачата: {task_description}

Контекст на студентот:
- Ниво на студирање: {student_context.get('study_level', 'факултет')}
- Насока на студирање: {student_context.get('study_direction', 'општа')}
- Дневни часови за учење: {student_context.get('daily_study_hours', 4)} часа
{history_context}

Ве молиме дајте:
1. Проценето потребно време во часови (биди реален, вклучи паузи)
2. Ниво на доверба (0-100%)
3. Распределба на времето (подготовка, главна работа, ревизија)
4. Проценка на тежината (лесна/умерена/предизвикувачка/многу_предизвикувачка)
5. Клучни фактори што влијаат на проценката
6. Препорачан пристап за учење
7. Потенцијални предизвици на кои треба да се внимава

Одговори во JSON формат:
{{
    "estimated_hours": <број_со_децимала>,
    "confidence_percentage": <цел_број>,
    "time_breakdown": {{
        "preparation": <број_со_децимала>,
        "active_work": <број_со_децимала>,
        "review_consolidation": <број_со_децимала>
    }},
    "difficulty_level": "<ниво>",
    "key_factors": ["фактор1", "фактор2", "фактор3"],
    "recommended_strategy": "<детален_пристап>",
    "potential_challenges": ["предизвик1", "предизвик2"]
}}

ВАЖНО: Сите текстуални описи во JSON треба да бидат на ЧИСТ МАКЕДОНСКИ јазик.
Користи ги македонските форми:
- 'ќе' наместо 'ће' 
- 'те' наместо 'ти'
- 'е' наместо 'је'
- македонска граматика (не српска)
Пример: "Ова ќе те помогне" НЕ "Ово ће ти помоћи"."""

    @staticmethod
    def quiz_generation_prompt(
        content: str,
        quiz_type: str,
        difficulty: str,
        num_questions: int,
        language: str = "mk"  # Default to Macedonian
    ) -> str:
        """Generate prompt for quiz creation - DEFAULTS TO MACEDONIAN"""

        if language == "mk":
            return f"""Генерирај {difficulty} {quiz_type} квиз со {num_questions} прашања базирани на следната содржина.

Содржина:
{content[:2000]}

Барања:
- Тежина: {difficulty}
- Тип на прашање: {quiz_type}
- Број на прашања: {num_questions}

За секое прашање, дај:
1. Јасен текст на прашањето
2. Точен одговор
3. За повеќекратен избор: 4 опции (А, Б, В, Г)
4. Краток образложение на точниот одговор

Одговори во JSON формат:
{{
    "questions": [
        {{
            "question_text": "<прашање_на_македонски>",
            "question_type": "{quiz_type}",
            "correct_answer": "<одговор>",
            "options": {{"А": "...", "Б": "...", "В": "...", "Г": "..."}},
            "explanation": "<објаснување>"
        }}
    ]
}}

ВАЖНО: Сите прашања и одговори МОРА да бидат на ЧИСТ МАКЕДОНСКИ јазик (не српски).
Користи:
- 'ќе' наместо 'ће'
- 'те' наместо 'ти' 
- 'е' наместо 'је'
- македонска граматика
Пример: "Која е разликата..." НЕ "Која је разлика..."."""
        else:
            # English version if explicitly requested
            return f"""Generate a {difficulty} {quiz_type} quiz with {num_questions} questions based on the following content.

Content:
{content[:2000]}

Requirements:
- Difficulty: {difficulty}
- Question Type: {quiz_type}
- Number of Questions: {num_questions}

For each question, provide:
1. Clear question text
2. Correct answer
3. For multiple choice: 4 options (A, B, C, D)
4. Brief explanation of the correct answer

Respond in JSON format:
{{
    "questions": [
        {{
            "question_text": "<question>",
            "question_type": "{quiz_type}",
            "correct_answer": "<answer>",
            "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
            "explanation": "<explanation>"
        }}
    ]
}}"""

    @staticmethod
    def study_planning_prompt(
        tasks: list,
        available_hours: float,
        preferences: Dict
    ) -> str:
        """Generate prompt for study schedule planning - IN MACEDONIAN"""

        tasks_str = "\n".join([
            f"- {task.get('description', 'Задача')} "
            f"(~{task.get('estimated_hours', 2)}ч, "
            f"рок: {task.get('deadline', 'нема')})"
            for task in tasks
        ])

        return f"""Креирај оптимизиран распоред за учење за овие задачи:

Задачи:
{tasks_str}

Достапно време за учење: {available_hours} часа
Префериран стил на учење: {preferences.get('learning_style', 'прилагодлив')}
Преферирано темпо на учење: {preferences.get('study_pace', 'умерено')}
Макс. должина на сесија: {preferences.get('max_session_length', 2)} часа

Креирај реален распоред што:
1. Ги приоритизира итните/важните задачи
2. Ја почитува максималната должина на сесиите
3. Вклучува соодветни паузи
4. Го зема предвид когнитивното оптоварување (алтернира тешки/лесни задачи)
5. Овозможува резервно време за неочекувани проблеми

Одговори во JSON формат:
{{
    "schedule": [
        {{
            "task": "<опис_на_задача>",
            "start_time": "<предложено_време>",
            "duration_hours": <број_со_децимала>,
            "priority": "<висок/среден/низок>",
            "notes": "<образложение_за_распоредот>"
        }}
    ],
    "total_scheduled_hours": <број_со_децимала>,
    "feasibility_score": <0-100>,
    "recommendations": ["совет1", "совет2"]
}}

ВАЖНО: Сите текстуални описи треба да бидат на ЧИСТ МАКЕДОНСКИ јазик (не српски).
Користи македонски форми: 'ќе', 'те', 'е', македонска граматика.
Пример: "Ова ќе те помогне" НЕ "Ово ће ти помоћи"."""

    @staticmethod
    def content_summary_prompt(
        content: str,
        summary_type: str = "concise",
        language: str = "mk"  # Default to Macedonian
    ) -> str:
        """Generate prompt for content summarization - DEFAULTS TO MACEDONIAN"""

        if language == "mk":
            summary_styles = {
                "concise": "краток, во формат на точки",
                "detailed": "опширен, во формат на параграфи",
                "exam_prep": "фокусиран на клучни концепти и веројатни испитни прашања"
            }

            style = summary_styles.get(summary_type, summary_styles["concise"])

            return f"""Резимирај ја следнава образовна содржина во {style}.

Содржина:
{content[:3000]}

Вклучи:
1. Главни теми/концепти
2. Клучни точки и дефиниции
3. Важни примери или апликации
4. Врски помеѓу концептите

Одговори во JSON формат:
{{
    "summary": "<главно_резиме_на_македонски>",
    "key_concepts": ["концепт1", "концепт2", "концепт3"],
    "important_points": ["точка1", "точка2"],
    "study_tips": ["совет1", "совет2"]
}}

ВАЖНО: Целото резиме и сите описи МОРА да бидат на ЧИСТ МАКЕДОНСКИ јазик (не српски).
Користи:
- 'ќе' наместо 'ће'
- 'те' наместо 'ти'
- 'е' наместо 'је'
- македонска граматика
Пример: "Ова ќе те помогне да научиш" НЕ "Ово ће ти помоћи да научиш"."""
        else:
            # English version if explicitly requested
            summary_styles = {
                "concise": "brief, bullet-point format",
                "detailed": "comprehensive, paragraph format",
                "exam_prep": "focused on key concepts and likely exam questions"
            }

            style = summary_styles.get(summary_type, summary_styles["concise"])

            return f"""Summarize the following educational content in {style}.

Content:
{content[:3000]}


Include:
1. Main topics/concepts
2. Key points and definitions
3. Important examples or applications
4. Connections between concepts

Respond in JSON format:
{{
    "summary": "<main summary>",
    "key_concepts": ["concept1", "concept2", "concept3"],
    "important_points": ["point1", "point2"],
    "study_tips": ["tip1", "tip2"]
}}"""

    @staticmethod
    def question_answering_prompt(
        question: str,
        context: str,
        student_level: str = "факултет",
        language: str = "mk"  # Default to Macedonian
    ) -> str:
        """Generate prompt for answering student questions - DEFAULTS TO MACEDONIAN"""

        if language == "mk":
            return f"""Одговори на следното студентско прашање јасно и точно.

Ниво на студентот: {student_level}
Прашање: {question}

Контекст/Позадина:
{context[:1500] if context else "Нема дополнителен контекст"}

Твојот одговор треба да:
1. Директно да се однесува на прашањето
2. Да биде соодветен за {student_level} ниво
3. Да ги објаснува концептите јасно
4. Да дава примери ако е корисно
5. Да предложи поврзани теми за истражување

Одговори природно во корисен, едукативен тон на ЧИСТ МАКЕДОНСКИ јазик (не српски).
ВАЖНО: Користи македонски форми:
- 'ќе' наместо 'ће'
- 'те' наместо 'ти'
- 'е' наместо 'је'
- македонска граматика
Пример: "Ова ќе те помогне да разбереш" НЕ "Ово ће ти помоћи да разумеш"."""
        else:
            # English version if explicitly requested
            return f"""Answer the following student question clearly and accurately.

Student Level: {student_level}
Question: {question}

Context/Background:
{context[:1500] if context else "No additional context provided"}


Your answer should:
1. Directly address the question
2. Be appropriate for {student_level} level
3. Explain concepts clearly
4. Provide examples if helpful
5. Suggest related topics to explore

Respond naturally in a helpful, educational tone."""

    @staticmethod
    def intent_classification_prompt(user_message: str) -> str:
        """Generate prompt for classifying user intent - IN MACEDONIAN"""

        return f"""Класифицирај ја намерата на корисникот од оваа порака:

Порака: "{user_message}"

Можни намери:
- quiz_generation: Корисникот сака да генерира квиз
- time_estimation: Корисникот сака да проценува време за задача
- schedule_planning: Корисникот сака помош за планирање на распоредот
- question_answering: Корисникот има специфично прашање
- content_summary: Корисникот сака резиме на содржина
- general_chat: Општ разговор или поздрав
- file_upload: Корисникот прикачува студиски материјали

Одговори само со името на намерата, ништо друго."""

    @staticmethod
    def macedonian_support_prompt() -> str:
        """Additional context for Macedonian language support"""
        return """
Забелешка за македонскиот јазик:
- Одговарај природно на македонски (македонска кирилица или латиница како што е соодветно)
- Користи правилна образовна терминологија
- Одржувај формален но пријателски тон типичен за македонското образование
- Биди свесен за регионалниот образовен систем (БСК - Болоњски систем контекст)
- Користи македонски термини за образовни концепти (испит, колоквиум, семинарска работа, итн.)
- Прилагоди се на македонскиот академски календар и структура

КРИТИЧНО: Секогаш одговарај на македонски јазик освен ако корисникот експлицитно не побара друг јазик.
"""


# Prompt template selector
def get_prompt_template(
    prompt_type: PromptType,
    **kwargs
) -> str:
    """
    Get appropriate prompt template based on type

    Usage:
        prompt = get_prompt_template(
            PromptType.TASK_ESTIMATION,
            task_description="Study for math exam",
            student_context={...}
        )
    """
    templates = PromptTemplates()

    if prompt_type == PromptType.TASK_ESTIMATION:
        return templates.task_estimation_prompt(**kwargs)
    elif prompt_type == PromptType.QUIZ_GENERATION:
        return templates.quiz_generation_prompt(**kwargs)
    elif prompt_type == PromptType.STUDY_PLANNING:
        return templates.study_planning_prompt(**kwargs)
    elif prompt_type == PromptType.CONTENT_SUMMARY:
        return templates.content_summary_prompt(**kwargs)
    elif prompt_type == PromptType.QUESTION_ANSWERING:
        return templates.question_answering_prompt(**kwargs)
    else:
        raise ValueError(f"Unknown prompt type: {prompt_type}")


# System prompt selector
def get_system_prompt(agent_type: str) -> str:
    """Get system prompt for specific agent type"""
    prompts = {
        "study": PromptTemplates.STUDY_AGENT_SYSTEM,
        "time": PromptTemplates.TIME_AGENT_SYSTEM,
        "organization": PromptTemplates.ORGANIZATION_AGENT_SYSTEM,
    }
    return prompts.get(agent_type, PromptTemplates.STUDY_AGENT_SYSTEM)

