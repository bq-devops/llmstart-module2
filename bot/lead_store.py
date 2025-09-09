"""
Модуль для сохранения лидов в CSV файл.
"""

import csv
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional


class LeadStore:
    """Класс для работы с лидами в CSV файле."""
    
    def __init__(self, csv_file: str = "leads.csv") -> None:
        """
        Инициализация хранилища лидов.
        
        Args:
            csv_file: Путь к CSV файлу для сохранения лидов
        """
        self.csv_file = csv_file
        self.fieldnames = [
            'timestamp',
            'chat_id', 
            'client_name',
            'contact',
            'intent',
            'notes',
            'source',
            'status'
        ]
        
        # Создаем файл с заголовками, если он не существует
        self._ensure_csv_exists()
        
        logging.info("LeadStore инициализирован: %s", self.csv_file)
    
    def _ensure_csv_exists(self) -> None:
        """Создает CSV файл с заголовками, если он не существует."""
        if not os.path.exists(self.csv_file):
            try:
                with open(self.csv_file, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                    writer.writeheader()
                logging.info("Создан новый CSV файл: %s", self.csv_file)
            except Exception as e:
                logging.error("Ошибка создания CSV файла: %s", str(e))
                raise
    
    def save_lead(self, 
                  chat_id: int,
                  contact: str,
                  intent: str,
                  notes: str = "",
                  client_name: str = "",
                  status: str = "new") -> bool:
        """
        Сохраняет лид в CSV файл.
        
        Args:
            chat_id: ID чата в Telegram
            contact: Контактные данные (телефон/email/username)
            intent: Потребность клиента
            notes: Дополнительные заметки (рекомендация от LLM)
            client_name: Имя клиента (если указано)
            status: Статус лида (new/qualified/rejected)
            
        Returns:
            True если лид успешно сохранен, False в случае ошибки
        """
        try:
            # Формируем данные лида
            lead_data = {
                'timestamp': datetime.now().isoformat(),
                'chat_id': str(chat_id),
                'client_name': client_name,
                'contact': contact,
                'intent': intent,
                'notes': notes,
                'source': 'telegram',
                'status': status
            }
            
            # Записываем в CSV файл
            with open(self.csv_file, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
                writer.writerow(lead_data)
            
            logging.info("Лид сохранен: chat_id=%s, contact=%s, intent=%s", 
                        chat_id, contact[:20], intent[:30])
            return True
            
        except Exception as e:
            logging.error("Ошибка сохранения лида: %s", str(e))
            return False
    
    def save_lead_from_dialog(self, 
                             chat_id: int,
                             dialog_state: Dict[str, Any],
                             contact: str,
                             client_name: str = "") -> bool:
        """
        Сохраняет лид на основе состояния диалога.
        
        Args:
            chat_id: ID чата в Telegram
            dialog_state: Состояние диалога с ответами
            contact: Контактные данные
            client_name: Имя клиента
            
        Returns:
            True если лид успешно сохранен, False в случае ошибки
        """
        try:
            # Формируем intent из ответов
            answers = dialog_state.get('answers', {})
            intent = answers.get('intent', 'Не указано')
            
            # Формируем notes из рекомендации LLM
            notes = dialog_state.get('last_llm_suggestion', '')
            
            # Если нет рекомендации, формируем краткое резюме
            if not notes:
                budget = answers.get('budget', 'не указан')
                timeline = answers.get('timeline', 'не указаны')
                priority = answers.get('priority', 'не указаны')
                notes = f"Бюджет: {budget}, Сроки: {timeline}, Приоритет: {priority}"
            
            return self.save_lead(
                chat_id=chat_id,
                contact=contact,
                intent=intent,
                notes=notes,
                client_name=client_name,
                status="new"
            )
            
        except Exception as e:
            logging.error("Ошибка сохранения лида из диалога: %s", str(e))
            return False
    
    def get_leads_count(self) -> int:
        """
        Возвращает количество сохраненных лидов.
        
        Returns:
            Количество строк в CSV файле (без заголовка)
        """
        try:
            if not os.path.exists(self.csv_file):
                return 0
            
            with open(self.csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                # Пропускаем заголовок и считаем строки
                return sum(1 for row in reader) - 1
                
        except Exception as e:
            logging.error("Ошибка подсчета лидов: %s", str(e))
            return 0


# Глобальный экземпляр хранилища лидов
_lead_store: Optional[LeadStore] = None


def get_lead_store() -> LeadStore:
    """Получить экземпляр хранилища лидов (ленивая инициализация)."""
    global _lead_store
    if _lead_store is None:
        _lead_store = LeadStore()
    return _lead_store
