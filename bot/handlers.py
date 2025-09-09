"""
Обработчики команд и сообщений для диалога с пользователями.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from .llm_client import get_llm_client

# Глобальное хранилище состояния диалогов в памяти
dialog_states: Dict[int, Dict[str, Any]] = {}

# Роутер для обработчиков
router = Router()


def get_dialog_state(chat_id: int) -> Dict[str, Any]:
    """Получить состояние диалога для чата."""
    if chat_id not in dialog_states:
        dialog_states[chat_id] = {
            'stage': 'greeting',
            'answers': {},
            'last_llm_suggestion': '',
            'started_at': datetime.now().isoformat()
        }
    return dialog_states[chat_id]


def is_returning_user(chat_id: int) -> bool:
    """Проверить, является ли пользователь возвратным (есть незавершенная сессия)."""
    if chat_id not in dialog_states:
        return False
    
    state = dialog_states[chat_id]
    current_stage = state.get('stage', 'greeting')
    
    # Возвратный пользователь, если диалог не завершен
    return current_stage not in ['done', 'greeting']


def get_continuation_message(chat_id: int) -> str:
    """Получить сообщение для продолжения диалога возвратного пользователя."""
    state = get_dialog_state(chat_id)
    current_stage = state.get('stage', 'greeting')
    
    if current_stage == 'qualifying':
        answers = state.get('answers', {})
        if 'intent' not in answers:
            return "Продолжим нашу беседу! Расскажите, что вас интересует?"
        elif 'budget' not in answers:
            return "Какой у вас примерный бюджет на этот проект?"
        elif 'timeline' not in answers:
            return "Когда бы вы хотели получить готовый результат?"
        elif 'priority' not in answers:
            return "Что для вас наиболее важно в этом проекте?"
    
    elif current_stage == 'offering':
        return "Хотели бы оставить контакт для обсуждения деталей?"
    
    elif current_stage == 'collecting_contact':
        return "Пожалуйста, оставьте ваш контакт для связи."
    
    return "Продолжим нашу беседу!"


def update_dialog_stage(chat_id: int, stage: str) -> None:
    """Обновить стадию диалога."""
    state = get_dialog_state(chat_id)
    state['stage'] = stage
    logging.info("Диалог chat_id=%s перешел в стадию: %s", chat_id, stage)


def save_answer(chat_id: int, question: str, answer: str) -> None:
    """Сохранить ответ пользователя."""
    state = get_dialog_state(chat_id)
    state['answers'][question] = answer
    logging.info("Сохранен ответ chat_id=%s: %s = %s", chat_id, question, answer[:50])


@router.message(Command("start"))
async def handle_start(message: types.Message) -> None:
    """Обработчик команды /start - приветствие нового пользователя или продолжение диалога."""
    chat_id = message.chat.id
    
    # Проверяем, является ли пользователь возвратным
    if is_returning_user(chat_id):
        logging.info("/start от возвратного пользователя chat_id=%s", chat_id)
        
        continuation_text = get_continuation_message(chat_id)
        await message.answer(f"👋 С возвращением! {continuation_text}")
        
        # Продолжаем диалог с текущей стадии
        state = get_dialog_state(chat_id)
        current_stage = state.get('stage', 'greeting')
        
        if current_stage == 'qualifying':
            # Показываем клавиатуру для квалификации
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Нужен сайт"), KeyboardButton(text="Мобильное приложение")],
                    [KeyboardButton(text="Автоматизация"), KeyboardButton(text="Консультация")],
                ],
                resize_keyboard=True,
            )
            await message.answer("Выберите вариант или напишите свой:", reply_markup=kb)
        elif current_stage == 'offering':
            # Показываем клавиатуру для предложения
            kb = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Да, оставлю контакт"), KeyboardButton(text="Пока не готов")],
                ],
                resize_keyboard=True,
            )
            await message.answer("Выберите вариант:", reply_markup=kb)
        # Для collecting_contact не показываем клавиатуру, ждем ввод контакта
        
    else:
        # Новый пользователь - сброс состояния
        dialog_states[chat_id] = {
            'stage': 'greeting',
            'answers': {},
            'last_llm_suggestion': '',
            'started_at': datetime.now().isoformat()
        }
        
        logging.info("/start от нового пользователя chat_id=%s", chat_id)
        
        welcome_text = (
            "👋 Привет! Я помогу вам выбрать подходящие IT-услуги.\n\n"
            "Расскажите, пожалуйста, что вас интересует? "
            "Например, нужен ли вам сайт, мобильное приложение или автоматизация процессов?"
        )
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Нужен сайт"), KeyboardButton(text="Мобильное приложение")],
                [KeyboardButton(text="Автоматизация"), KeyboardButton(text="Консультация")],
            ],
            resize_keyboard=True,
        )
        
        await message.answer(welcome_text, reply_markup=kb)
        update_dialog_stage(chat_id, 'qualifying')


@router.message(Command("ping"))
async def handle_ping(message: types.Message) -> None:
    """Обработчик команды /ping."""
    logging.info("/ping от chat_id=%s", message.chat.id)
    await message.answer("pong")


@router.message(Command("reset"))
async def handle_reset(message: types.Message) -> None:
    """Обработчик команды /reset - сброс диалога."""
    chat_id = message.chat.id
    
    # Сбрасываем состояние диалога
    dialog_states[chat_id] = {
        'stage': 'greeting',
        'answers': {},
        'last_llm_suggestion': '',
        'started_at': datetime.now().isoformat()
    }
    
    logging.info("/reset от chat_id=%s", chat_id)
    await message.answer("✅ Диалог сброшен. Напишите /start для начала новой консультации.")


@router.message(Command("ask"))
async def handle_ask(message: types.Message) -> None:
    """Обработчик команды /ask <вопрос>."""
    question = message.text[5:].strip()  # Убираем "/ask " из начала
    
    if not question:
        await message.answer("Пожалуйста, задайте вопрос после команды /ask")
        return
    
    logging.info("/ask от chat_id=%s, длина_вопроса=%d", message.chat.id, len(question))
    
    # Показываем, что обрабатываем запрос
    await message.answer("🤔 Думаю над вашим вопросом...")
    
    try:
        llm_client = get_llm_client()
        answer = await llm_client.ask_question(question)
        await message.answer(answer)
    except Exception as e:
        logging.error("Ошибка при обработке /ask: %s", str(e))
        from .prompt import FALLBACK_MESSAGE
        await message.answer(FALLBACK_MESSAGE)


@router.message()
async def handle_any_message(message: types.Message) -> None:
    """Обработчик любых сообщений - основная логика диалога."""
    chat_id = message.chat.id
    user_text = message.text.strip()
    
    if not user_text:
        return
    
    state = get_dialog_state(chat_id)
    current_stage = state['stage']
    
    logging.info("Сообщение от chat_id=%s, стадия=%s, текст=%s", 
                chat_id, current_stage, user_text[:50])
    
    if current_stage == 'greeting':
        # Если пользователь написал что-то без команды, приветствуем
        await handle_start(message)
        
    elif current_stage == 'qualifying':
        # Стадия квалификации - задаем уточняющие вопросы
        await handle_qualifying_stage(message, user_text)
        
    elif current_stage == 'offering':
        # Стадия предложения услуг
        await handle_offering_stage(message, user_text)
        
    elif current_stage == 'collecting_contact':
        # Стадия сбора контактов
        await handle_contact_stage(message, user_text)
        
    else:
        # Неизвестная стадия - сбрасываем
        await handle_start(message)


async def handle_qualifying_stage(message: types.Message, user_text: str) -> None:
    """Обработка стадии квалификации - задаем уточняющие вопросы."""
    chat_id = message.chat.id
    state = get_dialog_state(chat_id)
    
    # Сохраняем первый ответ о потребности
    if 'intent' not in state['answers']:
        save_answer(chat_id, 'intent', user_text)
        
        # Задаем следующий вопрос
        next_question = (
            "Понятно! А какой у вас примерный бюджет на этот проект? "
            "Это поможет мне подобрать оптимальное решение."
        )
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="До 100,000 руб"), KeyboardButton(text="100,000 - 300,000 руб")],
                [KeyboardButton(text="300,000 - 500,000 руб"), KeyboardButton(text="Свыше 500,000 руб")],
            ],
            resize_keyboard=True,
        )
        
        await message.answer(next_question, reply_markup=kb)
        
    elif 'budget' not in state['answers']:
        save_answer(chat_id, 'budget', user_text)
        
        # Задаем вопрос о сроках
        next_question = (
            "Отлично! А когда бы вы хотели получить готовый результат? "
            "Это поможет спланировать работу."
        )
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="В течение месяца"), KeyboardButton(text="1-2 месяца")],
                [KeyboardButton(text="2-3 месяца"), KeyboardButton(text="Не спешу")],
            ],
            resize_keyboard=True,
        )
        
        await message.answer(next_question, reply_markup=kb)
        
    elif 'timeline' not in state['answers']:
        save_answer(chat_id, 'timeline', user_text)
        
        # Задаем вопрос о контексте/приоритетах
        next_question = (
            "Понятно! А что для вас наиболее важно в этом проекте? "
            "Например, скорость разработки, качество, уникальный дизайн или что-то другое?"
        )
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Скорость разработки"), KeyboardButton(text="Качество")],
                [KeyboardButton(text="Уникальный дизайн"), KeyboardButton(text="Простота использования")],
                [KeyboardButton(text="Другое")],
            ],
            resize_keyboard=True,
        )
        
        await message.answer(next_question, reply_markup=kb)
        
    elif 'priority' not in state['answers']:
        save_answer(chat_id, 'priority', user_text)
        
        # Переходим к стадии предложения
        update_dialog_stage(chat_id, 'offering')
        await handle_offering_stage(message, user_text)


async def handle_offering_stage(message: types.Message, user_text: str) -> None:
    """Обработка стадии предложения услуг."""
    chat_id = message.chat.id
    state = get_dialog_state(chat_id)
    
    # Формируем рекомендацию на основе ответов
    try:
        llm_client = get_llm_client()
        
        from .prompt import RECOMMENDATION_PROMPT
        
        context = f"""
        Потребность клиента: {state['answers'].get('intent', 'не указано')}
        Бюджет: {state['answers'].get('budget', 'не указано')}
        Сроки: {state['answers'].get('timeline', 'не указано')}
        Приоритеты: {state['answers'].get('priority', 'не указано')}
        """
        
        # Формируем структурированный запрос
        question = f"{RECOMMENDATION_PROMPT}\n\nИнформация о клиенте:\n{context}"
        recommendation = await llm_client.ask_question(question)
        
        state['last_llm_suggestion'] = recommendation
        
        response = (
            f"📋 Основываясь на ваших ответах, рекомендую:\n\n"
            f"{recommendation}\n\n"
            f"Хотели бы оставить контакт для обсуждения деталей?"
        )
        
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Да, оставлю контакт"), KeyboardButton(text="Пока не готов")],
            ],
            resize_keyboard=True,
        )
        
        await message.answer(response, reply_markup=kb)
        update_dialog_stage(chat_id, 'collecting_contact')
        
    except Exception as e:
        logging.error("Ошибка при формировании рекомендации: %s", str(e))
        from .prompt import FALLBACK_MESSAGE
        await message.answer(FALLBACK_MESSAGE)
        update_dialog_stage(chat_id, 'collecting_contact')


async def handle_contact_stage(message: types.Message, user_text: str) -> None:
    """Обработка стадии сбора контактов."""
    chat_id = message.chat.id
    
    if user_text.lower() in ['да', 'да, оставлю контакт', 'да, оставлю']:
        contact_request = (
            "Отлично! Пожалуйста, оставьте ваш контакт для связи:\n"
            "• Телефон\n"
            "• Telegram username\n"
            "• Email\n\n"
            "Напишите любой удобный способ связи."
        )
        
        await message.answer(contact_request)
        
    elif user_text.lower() in ['нет', 'пока не готов', 'не готов']:
        farewell = (
            "Понятно! Если передумаете, всегда можете написать /start "
            "для новой консультации. Удачи! 😊"
        )
        
        await message.answer(farewell)
        update_dialog_stage(chat_id, 'done')
        
    else:
        # Пользователь оставил контакт
        save_answer(chat_id, 'contact', user_text)
        
        # Сохраняем лид в CSV
        try:
            from .lead_store import get_lead_store
            
            lead_store = get_lead_store()
            success = lead_store.save_lead_from_dialog(
                chat_id=chat_id,
                dialog_state=state,
                contact=user_text,
                client_name=""  # Имя не собираем отдельно
            )
            
            if success:
                success_message = (
                    "✅ Спасибо! Ваш контакт сохранен.\n\n"
                    "Наш менеджер свяжется с вами в ближайшее время "
                    "для обсуждения деталей проекта.\n\n"
                    "Если у вас есть вопросы, пишите /start для новой консультации!"
                )
                logging.info("Лид успешно сохранен в CSV: chat_id=%s", chat_id)
            else:
                success_message = (
                    "✅ Спасибо! Ваш контакт получен.\n\n"
                    "Наш менеджер свяжется с вами в ближайшее время.\n\n"
                    "Если у вас есть вопросы, пишите /start для новой консультации!"
                )
                logging.warning("Не удалось сохранить лид в CSV: chat_id=%s", chat_id)
                
        except Exception as e:
            logging.error("Ошибка при сохранении лида: %s", str(e))
            success_message = (
                "✅ Спасибо! Ваш контакт получен.\n\n"
                "Наш менеджер свяжется с вами в ближайшее время.\n\n"
                "Если у вас есть вопросы, пишите /start для новой консультации!"
            )
        
        await message.answer(success_message)
        update_dialog_stage(chat_id, 'done')
        
        logging.info("Контакт собран от chat_id=%s: %s", chat_id, user_text[:50])
