"""
Utilidades y helpers para el sistema
Contiene funciones comunes aplicando principio DRY
"""
import uuid
import random
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional


logger = logging.getLogger(__name__)


class IdGenerator:
    """
    Generador de IDs únicos
    
    Principio Single Responsibility: Solo genera IDs
    """
    
    @staticmethod
    def generate_unique_id() -> str:
        """Genera un ID único corto"""
        return str(uuid.uuid4())[:8]
    
    @staticmethod
    def generate_loan_id() -> str:
        """Genera un ID específico para préstamos"""
        return f"PREST-{datetime.now().strftime('%Y%m%d')}-{IdGenerator.generate_unique_id()}"


class ResponsePhrases:
    """
    Frases variadas para respuestas naturales
    
    Principio Single Responsibility: Solo manejo de frases
    """
    
    SALUDOS = [
        "¡Hola! ¡Qué gusto tenerte aquí!",
        "¡Bienvenido de vuelta!",
        "¡Hola! Me alegra que estés aquí.",
        "¡Qué bueno verte por aquí!",
        "¡Hola! Espero que tengas un excelente día."
    ]
    
    OPCIONES_MENU = [
        "Puedo ayudarte a gestionar tu biblioteca personal. Puedes agregar libros nuevos, ver tu lista de libros, prestar libros a tus amigos, registrar devoluciones o consultar qué libros tienes prestados.",
        "Tengo varias opciones para ti: agregar libros a tu colección, listar todos tus libros, prestar un libro a alguien, devolver un libro que te regresaron, o ver tus préstamos activos.",
        "Puedo hacer varias cosas: agregar libros nuevos a tu biblioteca, mostrarte qué libros tienes, ayudarte a prestar libros, registrar cuando te los devuelven, o decirte qué libros están prestados."
    ]
    
    PREGUNTAS_QUE_HACER = [
        "¿Qué te gustaría hacer hoy?",
        "¿En qué puedo ayudarte?",
        "¿Qué necesitas?",
        "¿Cómo puedo ayudarte con tu biblioteca?",
        "¿Qué quieres hacer?"
    ]
    
    ALGO_MAS = [
        "¿Hay algo más en lo que pueda ayudarte?",
        "¿Necesitas algo más?",
        "¿Qué más puedo hacer por ti?",
        "¿Te ayudo con algo más?",
        "¿Hay algo más que quieras hacer?"
    ]
    
    CONFIRMACIONES = [
        "¡Perfecto!",
        "¡Excelente!",
        "¡Genial!",
        "¡Muy bien!",
        "¡Estupendo!"
    ]
    
    DESPEDIDAS = [
        "¡Hasta luego! Que disfrutes tu lectura.",
        "¡Nos vemos pronto! Espero que disfrutes tus libros.",
        "¡Adiós! Fue un gusto ayudarte con tu biblioteca.",
        "¡Hasta la próxima! Feliz lectura.",
        "¡Que tengas un excelente día! Disfruta tus libros."
    ]
    
    @classmethod
    def get_random_phrase(cls, phrase_list: List[str]) -> str:
        """
        Selecciona una frase aleatoria de una lista
        
        Args:
            phrase_list: Lista de frases
        
        Returns:
            Frase aleatoria
        """
        return random.choice(phrase_list) if phrase_list else ""


class ValidationUtils:
    """
    Utilidades para validación de datos
    
    Principio Single Responsibility: Solo validaciones
    """
    
    @staticmethod
    def validate_book_title(title: str) -> tuple[bool, str]:
        """
        Valida un título de libro
        
        Args:
            title: Título a validar
        
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if not title:
            return False, "El título es requerido"
        
        title = title.strip()
        if len(title) == 0:
            return False, "El título no puede estar vacío"
        
        if len(title) > 200:
            return False, "El título es demasiado largo (máximo 200 caracteres)"
        
        return True, ""
    
    @staticmethod
    def validate_author_name(author: str) -> tuple[bool, str]:
        """
        Valida un nombre de autor
        
        Args:
            author: Nombre del autor
        
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if not author:
            return True, ""  # El autor es opcional
        
        author = author.strip()
        if len(author) > 100:
            return False, "El nombre del autor es demasiado largo (máximo 100 caracteres)"
        
        return True, ""
    
    @staticmethod
    def validate_person_name(person: str) -> tuple[bool, str]:
        """
        Valida el nombre de una persona para préstamos
        
        Args:
            person: Nombre de la persona
        
        Returns:
            Tuple (es_válido, mensaje_error)
        """
        if not person:
            return True, ""  # Se usará "un amigo" por defecto
        
        person = person.strip()
        if len(person) > 50:
            return False, "El nombre de la persona es demasiado largo (máximo 50 caracteres)"
        
        return True, ""
    
    @staticmethod
    def normalize_search_term(term: str) -> Optional[str]:
        """
        Normaliza un término de búsqueda
        
        Args:
            term: Término a normalizar
        
        Returns:
            Término normalizado o None si es inválido
        """
        if not term:
            return None
        
        normalized = term.strip().lower()
        return normalized if len(normalized) > 0 else None


class PaginationHelper:
    """
    Helper para paginación de resultados
    
    Principio Single Responsibility: Solo lógica de paginación
    """
    
    def __init__(self, items_per_page: int = 10):
        """
        Constructor
        
        Args:
            items_per_page: Elementos por página
        """
        self.items_per_page = items_per_page
    
    def paginate(self, items: List[Any], page: int = 0) -> Dict[str, Any]:
        """
        Pagina una lista de elementos
        
        Args:
            items: Lista de elementos
            page: Número de página (comenzando en 0)
        
        Returns:
            Diccionario con información de paginación
        """
        total_items = len(items)
        total_pages = (total_items + self.items_per_page - 1) // self.items_per_page
        
        if page < 0:
            page = 0
        elif page >= total_pages and total_pages > 0:
            page = total_pages - 1
        
        start_index = page * self.items_per_page
        end_index = min(start_index + self.items_per_page, total_items)
        
        current_items = items[start_index:end_index] if items else []
        
        return {
            "items": current_items,
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_items,
            "has_next": page < total_pages - 1,
            "has_previous": page > 0,
            "start_index": start_index,
            "end_index": end_index,
            "items_in_page": len(current_items)
        }


class DateUtils:
    """
    Utilidades para manejo de fechas
    
    Principio Single Responsibility: Solo operaciones con fechas
    """
    
    @staticmethod
    def format_date_spanish(date: datetime) -> str:
        """
        Formatea una fecha en español
        
        Args:
            date: Fecha a formatear
        
        Returns:
            Fecha formateada en español
        """
        months = [
            "enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
        ]
        
        day = date.day
        month = months[date.month - 1]
        year = date.year

        return f"{day} de {month} de {year}"
    