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

    verdict: str  
    hard_skills_analysis: str
    soft_skills_analysis: str  
    personal_roadmap: List[str]  


class LogTurn(BaseModel):
   
    turn_id: int
    agent_visible_message: str 
    user_message: str  
    internal_thoughts: str  

class InterviewLog(BaseModel):

    participant_name: str
    turns: List[LogTurn]
    final_feedback: str = ""
