
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
from pathlib import Path
import uuid
from config_itmo import OPEN_AI_API_KEY
from langchain_openai import ChatOpenAI
from req_resp_itmo import Request_class
from agent_itmo import interview_graph

app = FastAPI(title="AI Interview System")

# CORS для разрешения запросов с frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене укажите конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

        report = result['final_report']

        # Путь к JSON-логу, который сохранил граф (final_report_agent)
        log_file_path = result.get('log_file_path')
        if log_file_path:
            log_name = Path(log_file_path).name
            log_file = f"interview_logs/{log_name}"
        else:
            log_file = None
        
        return {
            'finished': True,
            'log_file': log_file,
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


# Раздача статических файлов (frontend)
static_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
def root():
    """Главная страница - возвращает frontend"""
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        'message': 'AI Interview System',
        'endpoints': {
            'POST /start': 'Начать интервью',
            'POST /answer': 'Отправить ответ'
        }
    }

