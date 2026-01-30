
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import uuid
from config_itmo import OPEN_AI_API_KEY
from langchain_openai import ChatOpenAI
from req_resp_itmo import Request_class
from agent_itmo import interview_graph, save_single_interview_log, INTERVIEW_LOGS_DIR

app = FastAPI(title="AI Interview System")

#сесси тут держим
sessions: Dict[str, Dict] = {}



LLM_MODEL = 'gpt-4o'

llm = ChatOpenAI(
    api_key=OPEN_AI_API_KEY,
    model=LLM_MODEL,
    temperature=0.4
)

#да повторил класс 
class StartRequest(BaseModel):
    name: str
    position: str
    grade: str
    experience: str

class AnswerRequest(BaseModel):
    session_id: str
    answer: str



@app.post("/start")
def start_interview(req: StartRequest):
    """
    Начать интервью. Возвращает session_id и первый вопрос.
    
    curl -X POST http://localhost:8000/start \
      -H "Content-Type: application/json" \
      -d '{"name":"Иван","position":"Python Dev","grade":"Junior","experience":"3 месяца и пет проект на django"}'
    """
    # +++++ Создаем сессию +++++
    session_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": session_id}}
    
    first_request = Request_class(
        name=req.name,
        position=req.position,
        grade=req.grade,
        experience=req.experience
    )
    
    initial_state = {
        'first_request': first_request,
        'is_finish': 'no',
        'context_interview': [],
        'current_question': None,
        'turn_count': 0,
        'llm': llm,
        'final_report': None,
        'difficulty_adjustment': 'same'
    }
    
    # первый запросик
    result = interview_graph.invoke(initial_state, config)
    
    #фиксируем сессию
    sessions[session_id] = {
        'config': config,
        'state': result
    }
    
    return {
        'session_id': session_id,
        'question': result['current_question'].question_of_interview_agent,
        'turn_id': result['turn_count']
    }


@app.post("/answer")
def submit_answer(req: AnswerRequest):
    """
    Отправить ответ. Возвращает следующий вопрос или финальный отчет.
    
    curl -X POST http://localhost:8000/answer \
      -H "Content-Type: application/json" \
      -d '{"session_id":"xxx","answer":"мой ответ"}'
    """
    # проверяем сессию
    if req.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[req.session_id]
    
    current_state = session['state']
    current_state['user_input'] = req.answer
    
  
    result = interview_graph.invoke(
        current_state,
        session['config']
    )
    
    session['state'] = result
    

    if result.get('is_finish', 'no').lower().startswith('y'):
 
        log_path = str(INTERVIEW_LOGS_DIR / f"interview_log_{req.session_id}.json")
        save_single_interview_log(result, log_path)
        
        report = result['final_report']
        
        return {
            'finished': True,
            'log_file': f"interview_logs/interview_log_{req.session_id}.json",
            'verdict': report.verdict,
            'hard_skills': report.hard_skills_analysis,
            'soft_skills': report.soft_skills_analysis,
            'roadmap': report.personal_roadmap
        }
    

    return {
        'finished': False,
        'question': result['current_question'].question_of_interview_agent,
        'turn_id': result['turn_count']
    }


@app.get("/")
def root():
    return {
        'message': 'AI Interview System',
        'endpoints': {
            'POST /start': 'Начать интервью',
            'POST /answer': 'Отправить ответ'
        }
    }

