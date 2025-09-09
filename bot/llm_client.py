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
        
        # Создаем клиент с минимальными параметрами для совместимости
        try:
            # Пробуем создать клиент с base_url
            self.client = openai.OpenAI(
                base_url=self.base_url,
                api_key=self.api_key
            )
        except Exception as e:
            if "proxies" in str(e) or "unexpected keyword argument" in str(e):
                # Fallback для проблемных версий openai - используем httpx напрямую
                logging.warning("Используем fallback инициализацию LLM клиента: %s", str(e))
                import httpx
                # Создаем клиент с кастомным http_client
                http_client = httpx.Client()
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    http_client=http_client
                )
            else:
                raise
        
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
            
            if response.choices and len(response.choices) > 0:
                answer = response.choices[0].message.content
                logging.info("LLM ответ получен, длина: %d символов", len(answer))
                return answer or "Извините, не удалось получить ответ."
            else:
                logging.error("LLM вернул пустой ответ")
                from .prompt import FALLBACK_MESSAGE
                return FALLBACK_MESSAGE
            
        except Exception as e:
            logging.error("Ошибка LLM: %s", str(e))
            from .prompt import FALLBACK_MESSAGE
            return FALLBACK_MESSAGE


# Глобальный экземпляр клиента
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Получить экземпляр LLM клиента (ленивая инициализация)."""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
