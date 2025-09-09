"""
OpenAI-совместимый клиент для работы с LLM.
"""

import logging
import os
from typing import Optional

import openai
from dotenv import load_dotenv

from .prompt import SYSTEM_PROMPT


class LLMClient:
    """Клиент для работы с OpenAI-совместимым API."""
    
    def __init__(self) -> None:
        """Инициализация клиента с параметрами из .env."""
        load_dotenv()
        
        self.base_url = os.getenv("LLM_BASE_URL")
        self.api_key = os.getenv("LLM_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
        
        if not self.base_url or not self.api_key:
            raise RuntimeError(
                "LLM_BASE_URL и LLM_API_KEY должны быть установлены в .env"
            )
        
        self.client = openai.OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
        
        logging.info("LLM клиент инициализирован: %s", self.base_url)
    
    async def ask_question(self, question: str) -> str:
        """
        Задать вопрос LLM и получить ответ.
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            Ответ LLM или fallback сообщение при ошибке
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            answer = response.choices[0].message.content
            logging.info("LLM ответ получен, длина: %d символов", len(answer))
            return answer or "Извините, не удалось получить ответ."
            
        except Exception as e:
            logging.error("Ошибка LLM: %s", str(e))
            return (
                "Сервис временно недоступен. "
                "Давайте обменяемся контактами для консультации."
            )


# Глобальный экземпляр клиента
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Получить экземпляр LLM клиента (ленивая инициализация)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
