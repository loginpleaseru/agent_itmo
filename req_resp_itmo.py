from pydantic import BaseModel, HttpUrl, Field
from typing import List,Optional, Any ,Literal

class Single_turn(BaseModel):
    turn_id : int
    agent_visible_message : str
    user_message : str
    internal_thoughts : str

class Request_class(BaseModel): 
    name : str
    position : str
    grade : str
    experience : str 

class Question_class(BaseModel):
     #че спросил че ответил
    turn_id: int
    question_of_interview_agent: str
    user_message: str

class ThinkingAgentResponse(BaseModel):
    #че подумал
    internal_thoughts: str
    is_finish: str  
    difficulty_adjustment: Literal['easier', 'same', 'harder']
    detected_off_topic: bool
    confidence_level: Literal['uncertain', 'moderate', 'confident']

class StopIntentResponse(BaseModel):
    wants_to_finish: str = Field(description="'yes' если пользователь хочет завершить интервью, 'no' если это обычный ответ на вопрос")
    


class Response_class(BaseModel): #мб удалить
    participant_name : str
    turns : List[Single_turn]
    final_feedback : str

class FinalReport(BaseModel):
    """Финальный отчёт интервью. Все поля — кратко, по делу."""

    verdict: str = Field(description="Краткий итоговый вердикт, 1-2 предложения")
    grade: Literal["Junior", "Middle", "Senior"] = Field(description="Оценка уровня кандидата по ответам")
    hiring_recommendation: Literal["Hire", "No Hire", "Strong Hire"] = Field(description="Рекомендация по найму")
    confidence_score: int = Field(ge=0, le=100, description="Уверенность системы в оценке, 0-100%")
    hard_skills_analysis: str = Field(
        description="Technical Review: ✅ Confirmed Skills (темы с точными ответами); ❌ Knowledge Gaps (темы с ошибками/«не знаю» + правильный ответ). Кратко, списком или таблицей."
    )
    soft_skills_analysis: str = Field(
        description="Clarity (понятность изложения), Honesty (честность/признание незнания), Engagement (встречные вопросы). Кратко."
    )
    personal_roadmap: List[str] = Field(
        description="Конкретные темы/технологии для подтягивания на основе пробелов, 3-7 пунктов"
    )  


class LogTurn(BaseModel):
   
    turn_id: int
    agent_visible_message: str 
    user_message: str  
    internal_thoughts: str  

class InterviewLog(BaseModel):

    participant_name: str
    turns: List[LogTurn]
    final_feedback: str = ""
