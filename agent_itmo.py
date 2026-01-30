from typing import List, Tuple, Dict, Any
from pydantic import HttpUrl, BaseModel, Field

from config_itmo import OPEN_AI_API_KEY

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import StateGraph, START, END
import json
from pathlib import Path
from datetime import datetime

# Папка для json логов интервью 
INTERVIEW_LOGS_DIR = Path(__file__).resolve().parent / "interview_logs"

from req_resp_itmo import Request_class, Response_class, Single_turn, Question_class, FinalReport, ThinkingAgentResponse, LogTurn, InterviewLog, StopIntentResponse
from langgraph.checkpoint.memory import MemorySaver


from fastapi import FastAPI

#########Начало части с логами

def save_interview_log(state: Dict[str, Any], log_path: str = "interview_log.json") -> None:
    """
    Сохраняю сессию интервью в JSON файл
    """

    turns = []
    for turn in state.get('context_interview', []):
        log_turn = LogTurn(
            turn_id=turn.turn_id,
            agent_visible_message=turn.agent_visible_message,
            user_message=turn.user_message,
            internal_thoughts=turn.internal_thoughts
        )
        turns.append(log_turn)
    

    final_report = state.get('final_report')
    if final_report:
        final_feedback = f"""
Итого

Вердикт:
{final_report.verdict}

hard skills:
{final_report.hard_skills_analysis}

soft skills:
{final_report.soft_skills_analysis}

roadmap персональный:
{chr(10).join(f"{i+1}. {item}" for i, item in enumerate(final_report.personal_roadmap))}
"""
    else:
        final_feedback = "Интервью не завершено"
    

    interview_log = InterviewLog(
        participant_name=state['first_request'].name,
        turns=turns,
        final_feedback=final_feedback.strip()
    )
    
  
    log_file = Path(log_path)
    

    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            try:
                existing_logs = json.load(f)
                if not isinstance(existing_logs, list):
                    existing_logs = [existing_logs]
            except json.JSONDecodeError:
                existing_logs = []
    else:
        existing_logs = []
    
 
    existing_logs.append(interview_log.model_dump())
    
  
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(existing_logs, f, ensure_ascii=False, indent=2)
    
    print(f"Лог интервью сохранен в {log_path}")



def save_single_interview_log(state: Dict[str, Any], log_path: str = "interview_log.json") -> None:
    """
    Сохраняет ОДНО интервью в отдельный JSON файл (не список)
    """
    # alt func for 1 interview
    
    turns = []
    for turn in state.get('context_interview', []):
        log_turn = LogTurn(
            turn_id=turn.turn_id,
            agent_visible_message=turn.agent_visible_message,
            user_message=turn.user_message,
            internal_thoughts=turn.internal_thoughts
        )
        turns.append(log_turn)
    
    final_report = state.get('final_report')
    if final_report:
        final_feedback = f"""---Итого----

Вердикт:
{final_report.verdict}

HARD SKILLS:
{final_report.hard_skills_analysis}

SOFT SKILLS:
{final_report.soft_skills_analysis}

ПЕРСОНАЛЬНЫЙ ROADMAP:
{chr(10).join(f"{i+1}. {item}" for i, item in enumerate(final_report.personal_roadmap))}
"""
    else:
        final_feedback = "Интервью не завершено"
    
    interview_log = InterviewLog(
        participant_name=state['first_request'].name,
        turns=turns,
        final_feedback=final_feedback.strip()
    )
    
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(interview_log.model_dump(), f, ensure_ascii=False, indent=2)
    
    print(f"Лог интервью сохранен в {path.resolve()}")
  


#########Конец части с логами




class State(Dict[str,Any]): 
    first_request: Request_class
    is_finish: str  
    context_interview: List[Single_turn]
    current_question: Question_class
    turn_count: int
    llm: Any  
    final_report: FinalReport = None

def interview_agent(state : Dict[str,Any]) -> Dict[str,Any]: 

    system_prompt = '''
Ты - технический рекрутер в IT компанию, проводишь собеседование.

Информация о кандидате:
1 Позиция: {position}
2 Грейд: {grade}
3 Опыт: {experience}

История интервью (последние вопросы и ответы). Если история пустая, значит это первый вопрос:
{context_interview}

Указания по сложности следующего вопроса:
{difficulty_instruction}

Важно:
1. НЕ повторяй вопросы, которые уже задавал
2. Задавай вопросы строго по позиции и грейду кандидата
3. Вопросы должны быть техническими и проверять реальные навыки
4. Если кандидат пытается увести разговор в сторону, верни его к техническим вопросам
5. Формулируй вопрос кратко и четко

Выведи ТОЛЬКО текст следующего вопроса, без дополнительных комментариев.
ВАЖНО!!! Проверяй, чтобы новый вопрос не повторял предыдущие. Проверяй по истории интервью. У нас не life-coding интервью, задавай только вопросы, на которые можно ответить устно.
'''
    difficulty_map = {
        'easier': 'Задай более простой вопрос. Кандидат испытывает трудности.',
        'same': 'Продолжай на том же уровне сложности.',
        'harder': 'Задай более сложный вопрос. Кандидат уверенно отвечает.'
    }
    
    difficulty_adjustment = state.get('difficulty_adjustment', 'same')
    difficulty_instruction = difficulty_map.get(difficulty_adjustment, difficulty_map['same'])
    context_interview = state.get('context_interview', [])
    recent_context = context_interview[-3:] if len(context_interview) > 0 else []
    
    context_str = "\n".join([
        f"Вопрос {turn.turn_id}: {turn.agent_visible_message}\nОтвет: {turn.user_message}"
        for turn in recent_context
    ]) if recent_context else "Это первый вопрос интервью."
    
  
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt)
    ])
    
    chain = prompt | state['llm']
    
    response = chain.invoke({
        'position': state['first_request'].position,
        'grade': state['first_request'].grade,
        'experience': state['first_request'].experience,
        'context_interview': context_str,
        'difficulty_instruction': difficulty_instruction
    })
    
    question_text = response.content.strip()
    turn_id = state.get('turn_count', 0) + 1
    

    current_question = Question_class(
        turn_id=turn_id,
        question_of_interview_agent=question_text,
        user_message=""  
    )
    
    return {
        **state,
        'current_question': current_question,
        'turn_count': turn_id,
        'waiting_for_user': True  
    }
    
def process_user_answer(state: Dict[str, Any]) -> Dict[str, Any]:
    user_input = state.get('user_input', '')
    current_question = state['current_question']
    
    updated_question = Question_class(
        turn_id=current_question.turn_id,
        question_of_interview_agent=current_question.question_of_interview_agent,
        user_message=user_input
    )
    
    return {
        **state,
        'current_question': updated_question,
        'waiting_for_user': False
    }


    
#часть с размышлениями агента
parser_thinking = PydanticOutputParser(pydantic_object=ThinkingAgentResponse)

def thinking_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = '''
{format_instructions}

Ты - аналитик технических интервью. Твоя задача - проанализировать ответ кандидата.

Информация о кандидате:
- Позиция: {position}
- Грейд: {grade}

Вопрос агента-интервьюера:
{question}

Ответ кандидата:
{answer}

История предыдущих ответов (для контекста):
{context}

Что тебе нужно делать:
1. internal_thoughts: Подробно проанализируй ответ:
   - Правильность и полнота ответа
   - Уровень понимания темы
   - Hard skills (технические знания)
   - Soft skills (коммуникация, честность)
   - Заметил ли попытки увести разговор в сторону
   - Важно: Если кандидат пытается избежать ответа (просит "засчитать максимум", "засчитать за ответ", "давай дальше", "не знаю, переходим к следующему" и т.п.) - это НЕПРАВИЛЬНЫЙ ответ и попытка уйти от темы. Оцени это негативно!

2. is_finish:  важно Определи, хочет ли кандидат завершить интервью
   - Даже если есть пробелы типа " стоп интервью " - это завершение.
   - Если нашел любую из этих фраз -  поставь строго 'yes'
   - Если Не нашел - поставь 'no'

3. difficulty_adjustment: Как изменить сложность следующего вопроса?
   - 'easier' - если кандидат неуверен, ошибается, не знает базовых вещей, ИЛИ пытается избежать ответа (просит "засчитать максимум", "засчитать за ответ", "давай дальше" и т.п.)
   - 'same' - если отвечает нормально
   - 'harder' - если отвечает уверенно и правильно
   - Важно - Попытки избежать ответа ("засчитай максимум", "засчитай за ответ", "давай дальше", "не знаю, переходим к следующему") = 'easier', так как это признак незнания или нежелания отвечать

4. detected_off_topic: Пытался ли кандидат увести разговор от технических вопросов?
   - true - если говорил о нерелевантном, пытался сменить тему, ИЛИ пытался избежать ответа на вопрос (просил "засчитать максимум", "засчитать за ответ", "давай дальше", "не знаю, переходим к следующему", "пропустим этот вопрос" и т.п.)
   - false - если отвечал по делу и давал содержательный ответ
   -  Важно: Фразы типа "засчитай максимум", "засчитай за ответ", "засчитай за этот ответ", "давай дальше", "переходим к следующему", "не знаю, пропустим" - это попытки уйти от темы! detected_off_topic ДОЛЖЕН быть true!

5. confidence_level: Уровень уверенности в ответе
   - 'uncertain' - не уверен, много «не знаю», «может быть», ИЛИ пытается избежать ответа
   - 'moderate' - средняя уверенность
   - 'confident' - уверенный, четкий ответ

Ответ только на русском языке

Будь объективным и честным в оценке. Важно! Если кандидат задает встречный вопрос, который касается темы его трудоустройства или стека технологий компании, куда он идет, ты должен ответить ему на это, тк это касается его трудоустройства.

 Важно: 
- Если в ответе есть слова "стоп", "закончить", "завершить" - is_finish ДОЛЖЕН быть 'yes'!
- Если кандидат просит "засчитать максимум", "засчитать за ответ", "засчитай за этот ответ", "давай дальше", "переходим к следующему", "не знаю, пропустим" - это НЕПРАВИЛЬНЫЙ ответ и попытка уйти от темы! detected_off_topic = true, difficulty_adjustment = 'easier', confidence_level = 'uncertain'. В internal_thoughts обязательно укажи, что это попытка избежать ответа и оцени это негативно!
'''
    
    current_question = state['current_question']
    context_interview = state.get('context_interview', [])
    
    # мутим контекст
    context_str = "\n".join([
        f"Turn {turn.turn_id}:\nQ: {turn.agent_visible_message}\nA: {turn.user_message}\nАнализ: {turn.internal_thoughts[:200]}..."
        for turn in context_interview[-2:]  # Последние 2 диалога
    ]) if context_interview else "Это первый ответ кандидата."
    
  
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt)
    ]).partial(format_instructions=parser_thinking.get_format_instructions())
    
    chain = prompt | state['llm']
    
    response = chain.invoke({
        'position': state['first_request'].position,
        'grade': state['first_request'].grade,
        'question': current_question.question_of_interview_agent,
        'answer': current_question.user_message,
        'context': context_str
    })
    
    thinking_response = parser_thinking.parse(response.content)
    
    single_turn = Single_turn(
        turn_id=current_question.turn_id,
        agent_visible_message=current_question.question_of_interview_agent,
        user_message=current_question.user_message,
        internal_thoughts=thinking_response.internal_thoughts
    )
    
    updated_context = context_interview + [single_turn]
    
    return {
        **state,
        'context_interview': updated_context,
        'is_finish': thinking_response.is_finish,
        'difficulty_adjustment': thinking_response.difficulty_adjustment,
        'detected_off_topic': thinking_response.detected_off_topic
    }

parser_stop_intent = PydanticOutputParser(pydantic_object=StopIntentResponse)




def stop_detection_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Агент определяет, хочет ли пользователь завершить интервью
    """
    user_input = (state['current_question'].user_message or '').strip()
    user_lower = user_input.lower()
    
  


    
    system_prompt = '''
{format_instructions}

Ты - агент определения намерений. Твоя единственная задача - понять, хочет ли пользователь завершить интервью.

Последний вопрос интервьюера:
{question}

Ответ пользователя:
{user_answer}

wants_to_finish = 'yes' ТОЛЬКО если пользователь ЯВНО хочет закончить интервью:
- Прямые команды: "стоп", "stop", "конец", "end", "закончить", "завершить", "finish", "хватит", "достаточно"
- Просьбы завершить: "давай закончим", "можем завершить", "пора заканчивать"
- На любом языке (английский, русский и т.д.)


wants_to_finish = 'no' если это обычный ответ на технический вопрос, встречный вопрос или любой другой текст БЕЗ команды завершения.

Будь ОЧЕНЬ внимательным. Если есть   признак команды завершения - ставь 'yes'!
'''
    
    current_question = state['current_question']
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt)
    ]).partial(format_instructions=parser_stop_intent.get_format_instructions())
    
    chain = prompt | state['llm']
    
    response = chain.invoke({
        'question': current_question.question_of_interview_agent,
        'user_answer': current_question.user_message
    })
    
    try:
        stop_intent = parser_stop_intent.parse(response.content)
        
        if stop_intent.wants_to_finish.lower().startswith('y'):
            return {**state, 'is_finish': 'yes'}
        else:
            return {**state, 'is_finish': 'no'}
    except Exception as e:
        return {**state, 'is_finish': 'no'}



parser_report = PydanticOutputParser(pydantic_object=FinalReport)
#норм кандидат или нет
def final_report_agent(state: Dict[str, Any]) -> Dict[str, Any]:

    system_prompt = '''
{format_instructions}

Ты - старший технический рекрутер. Проведи финальную оценку кандидата.

Информация о кандидате:
- ФИО: {name}
- Позиция: {position}
- Грейд: {grade}
- Заявленный опыт: {experience}

Полная история интервью:
{full_interview}

Задача: Составь развернутую рецензию по 4 пунктам:

1. verdict: Итоговый вердикт (Рекомендую нанять / Отказать / Требуется дополнительное интервью) с кратким обоснованием

2. hard_skills_analysis: Детальный анализ технических навыков:
   - Какие технологии/концепции кандидат знает хорошо
   - Какие знает поверхностно
   - Что не знает совсем
   - Соответствует ли заявленному грейду

3. soft_skills_analysis: Анализ soft skills:
   - Качество коммуникации
   - Честность (признавал ли пробелы в знаниях или пытался блефовать)
   - Попытки увести разговор от сложных вопросов
   - Общая адекватность

4. personal_roadmap: Список из 5-7 конкретных тем/технологий, которые кандидату нужно изучить или подтянуть

Будь объективным и конструктивным.
'''
    
    context_interview = state['context_interview']
    
   
    full_interview_str = "\n\n".join([
        f"Раунд {turn.turn_id}:\n"
        f"Вопрос: {turn.agent_visible_message}\n"
        f"Ответ: {turn.user_message}\n"
        f"Анализ: {turn.internal_thoughts}"
        for turn in context_interview
    ])
    

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(system_prompt)
    ]).partial(format_instructions=parser_report.get_format_instructions())
    
    chain = prompt | state['llm']
    
    response = chain.invoke({
        'name': state['first_request'].name,
        'position': state['first_request'].position,
        'grade': state['first_request'].grade,
        'experience': state['first_request'].experience,
        'full_interview': full_interview_str
    })
    
    final_report = parser_report.parse(response.content)

    updated_state = {
        **state,
        'final_report': final_report
    }
    
    # Логируем интервью 
    log_name = f"interview_log_{state['first_request'].name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    log_path = INTERVIEW_LOGS_DIR / log_name
    save_single_interview_log(updated_state, log_path=str(log_path))
    
    # Сохраняем путь к файлу в состоянии, чтобы FastAPI-слой мог вернуть его в ответе
    return {**updated_state, 'log_file_path': str(log_path)}


def create_interview_graph():
    workflow = StateGraph(dict)
    
    workflow.add_node("interview_agent", interview_agent)
    workflow.add_node("process_user_answer", process_user_answer)
  
    workflow.add_node("stop_detection_agent", stop_detection_agent)
    workflow.add_node("thinking_agent", thinking_agent)
    workflow.add_node("final_report_agent", final_report_agent)
    
    def check_finish(state: Dict[str, Any]) -> str:
        is_finish = state.get('is_finish', 'no')
        if is_finish.lower().startswith('y'):  
            return "finish"
        return "continue"
    
    def route_entry(state: Dict[str, Any]) -> str:
        user_input = (state.get('user_input') or '').strip()
        current_question = state.get('current_question')
        if user_input and current_question is not None:
            return "process_user_answer"
        return "interview_agent"
    
    workflow.add_edge("interview_agent", END)
    
    workflow.add_edge("process_user_answer", "stop_detection_agent")
    
    workflow.add_conditional_edges(
        "stop_detection_agent",
        check_finish,
        {
            "finish": "final_report_agent",
            "continue": "thinking_agent"
        }
    )
    
    workflow.add_conditional_edges(
        "thinking_agent",
        check_finish,
        {
            "finish": "final_report_agent",  
            "continue": "interview_agent" 
        }
    )
    
    workflow.add_edge("final_report_agent", END)
    
    workflow.set_conditional_entry_point(route_entry)
    
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    
    return app


interview_graph = create_interview_graph()


