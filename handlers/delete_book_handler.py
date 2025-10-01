"""
Handler para eliminar libros con confirmación (Funcionalidad nueva requerida)
Implementa diálogo de confirmación y validación de préstamos activos
"""
import logging
from typing import Optional

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response

from services.book_service import BookService
from services.loan_service import LoanService
from helpers.utils import ResponsePhrases, ValidationUtils, TextUtils
from factories.service_factory import get_service_factory


logger = logging.getLogger(__name__)


class DeleteBookIntentHandler(AbstractRequestHandler):
    """
    Handler para eliminar libros con confirmación y validaciones
    
    Funcionalidad nueva requerida por el proyecto.
    Incluye diálogo de confirmación y manejo de libros prestados.
    
    Principios aplicados:
    - Single Responsibility: Solo eliminar libros
    - Open/Closed: Extensible para nuevos tipos de validación
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """
        Verifica si puede manejar la request
        
        Args:
            handler_input: Input del handler
        
        Returns:
            True si puede manejar la request
        """
        return ask_utils.is_intent_name("EliminarLibroIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el intent de eliminar libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            # Obtener servicios
            book_service = self.service_factory.get_book_service(handler_input)
            loan_service = self.service_factory.get_loan_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener título del libro a eliminar
            titulo = ask_utils.get_slot_value(handler_input, "titulo")
            
            if not titulo:
                return self._request_book_title(handler_input)
            
            # Buscar el libro
            books = book_service.search_books_by_title(user_id, titulo)
            
            if not books:
                return self._handle_book_not_found(handler_input, titulo, book_service, user_id)
            
            if len(books) > 1:
                return self._handle_multiple_books(handler_input, books, titulo)
            
            # Un solo libro encontrado
            book = books[0]
            
            # Verificar estado de sesión para confirmación
            session_attrs = handler_input.attributes_manager.session_attributes
            
            if session_attrs.get("confirming_delete") == book.id:
                return self._process_confirmation(handler_input, book_service, loan_service, user_id, book)
            else:
                return self._request_confirmation(handler_input, book, loan_service, user_id)
            
        except Exception as e:
            logger.error(f"Error en DeleteBookHandler: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _request_book_title(self, handler_input) -> Response:
        """
        Solicita el título del libro a eliminar
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response solicitando título
        """
        prompts = [
            "¿Qué libro quieres eliminar?",
            "¿Cuál libro deseas eliminar de tu biblioteca?",
            "Dime el título del libro que quieres eliminar."
        ]
        
        speak_output = ResponsePhrases.get_random_phrase(prompts)
        ask_output = "¿Cuál es el título del libro que quieres eliminar?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_book_not_found(self, handler_input, titulo: str, 
                              book_service: BookService, user_id: str) -> Response:
        """
        Maneja el caso cuando no se encuentra el libro
        
        Args:
            handler_input: Input del handler
            titulo: Título buscado
            book_service: Servicio de libros
            user_id: ID del usuario
        
        Returns:
            Response con sugerencias
        """
        # Obtener algunos libros para sugerir
        all_books = book_service.get_all_books(user_id)
        
        speak_output = f"No encontré ningún libro con el título '{titulo}' en tu biblioteca. "
        
        if all_books:
            # Sugerir algunos libros disponibles
            sample_books = all_books[:3]
            titles = [f"'{book.titulo}'" for book in sample_books]
            
            if len(all_books) == 1:
                speak_output += f"Solo tienes {titles[0]}."
            elif len(all_books) <= 3:
                speak_output += f"Tienes: {TextUtils.format_list_natural(titles, 'y')}."
            else:
                speak_output += f"Por ejemplo, tienes: {TextUtils.format_list_natural(titles, 'y')}."
        else:
            speak_output += "De hecho, no tienes ningún libro en tu biblioteca."
        
        speak_output += " " + ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
        ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_multiple_books(self, handler_input, books: list, titulo: str) -> Response:
        """
        Maneja múltiples libros encontrados
        
        Args:
            handler_input: Input del handler
            books: Lista de libros encontrados
            titulo: Título buscado
        
        Returns:
            Response pidiendo especificidad
        """
        speak_output = f"Encontré varios libros que contienen '{titulo}': "
        
        book_descriptions = []
        for book in books[:3]:  # Mostrar máximo 3
            desc = f"'{book.titulo}'"
            if book.autor != "Desconocido":
                desc += f" de {book.autor}"
            book_descriptions.append(desc)
        
        speak_output += TextUtils.format_list_natural(book_descriptions, "y")
        
        if len(books) > 3:
            speak_output += f" y {len(books) - 3} más"
        
        speak_output += ". ¿Puedes ser más específico con el título completo?"
        ask_output = "¿Cuál es el título exacto del libro que quieres eliminar?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _request_confirmation(self, handler_input, book, loan_service: LoanService, user_id: str) -> Response:
        """
        Solicita confirmación antes de eliminar
        
        Args:
            handler_input: Input del handler
            book: Libro a eliminar
            loan_service: Servicio de préstamos
            user_id: ID del usuario
        
        Returns:
            Response solicitando confirmación
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs["confirming_delete"] = book.id
        session_attrs["delete_book_title"] = book.titulo
        
        # Verificar si está prestado
        active_loan = None
        active_loans = loan_service.get_active_loans(user_id)
        for loan in active_loans:
            if loan.libro_id == book.id:
                active_loan = loan
                break
        
        speak_output = f"¿Estás seguro de que quieres eliminar '{book.titulo}'"
        
        if book.autor != "Desconocido":
            speak_output += f" de {book.autor}"
        
        speak_output += "? "
        
        if active_loan:
            speak_output += f"Ten en cuenta que está prestado a {active_loan.persona}. "
            speak_output += "Si lo eliminas, también cancelaré el préstamo. "
        
        if book.total_prestamos > 0:
            prestamos_text = TextUtils.pluralize(book.total_prestamos, "vez", "veces")
            speak_output += f"Este libro ha sido prestado {book.total_prestamos} {prestamos_text}. "
        
        speak_output += "Di 'sí' para confirmar o 'no' para cancelar."
        ask_output = "¿Confirmas que quieres eliminarlo? Di 'sí' o 'no'."
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _process_confirmation(self, handler_input, book_service: BookService, 
                            loan_service: LoanService, user_id: str, book) -> Response:
        """
        Procesa la confirmación del usuario
        
        Args:
            handler_input: Input del handler
            book_service: Servicio de libros
            loan_service: Servicio de préstamos
            user_id: ID del usuario
            book: Libro a eliminar
        
        Returns:
            Response final
        """
        # Limpiar sesión
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs.pop("confirming_delete", None)
        session_attrs.pop("delete_book_title", None)
        
        # Intentar eliminar el libro usando el servicio
        success, message, deleted_book = book_service.delete_book(user_id, book_id=book.id)
        
        if success:
            # Si había préstamo activo, completarlo como cancelado
            active_loans = loan_service.get_active_loans(user_id)
            for loan in active_loans:
                if loan.libro_id == book.id:
                    loan_service.return_loan(user_id, loan_id=loan.id)
                    logger.info(f"Cancelled loan {loan.id} due to book deletion")
                    break
            
            # Construir respuesta de éxito
            confirmacion = ResponsePhrases.get_random_phrase(ResponsePhrases.CONFIRMACIONES)
            speak_output = f"{confirmacion} He eliminado '{book.titulo}' de tu biblioteca. "
            
            # Obtener estadísticas actualizadas
            stats = book_service.get_book_statistics(user_id)
            remaining_books = stats["total_books"]
            
            if remaining_books > 0:
                books_text = TextUtils.pluralize(remaining_books, "libro", "libros")
                speak_output += f"Ahora te quedan {remaining_books} {books_text}. "
            else:
                speak_output += "Ya no tienes más libros en tu biblioteca. "
            
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        else:
            # Error al eliminar
            speak_output = f"No pude eliminar el libro: {message}. "
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_error(self, handler_input) -> Response:
        """
        Maneja errores generales
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de error
        """
        # Limpiar sesión en caso de error
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs.pop("confirming_delete", None)
        session_attrs.pop("delete_book_title", None)
        
        speak_output = "Hubo un problema eliminando el libro. ¿Intentamos de nuevo?"
        ask_output = "¿Qué libro quieres eliminar?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """
        Extrae el user ID del handler input
        
        Args:
            handler_input: Input del handler
        
        Returns:
            User ID
        """
        return handler_input.request_envelope.context.system.user.user_id


class ConfirmDeleteHandler(AbstractRequestHandler):
    """
    Handler para manejar confirmaciones de eliminación (Yes/No intents)
    """
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar confirmaciones de eliminación"""
        session_attrs = handler_input.attributes_manager.session_attributes
        is_confirming = session_attrs.get("confirming_delete") is not None
        
        return (is_confirming and 
                (ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input) or
                 ask_utils.is_intent_name("AMAZON.NoIntent")(handler_input)))
    
    def handle(self, handler_input) -> Response:
        """
        Procesa confirmación o cancelación
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response apropiada
        """
        try:
            session_attrs = handler_input.attributes_manager.session_attributes
            book_title = session_attrs.get("delete_book_title", "el libro")
            
            if ask_utils.is_intent_name("AMAZON.YesIntent")(handler_input):
                # Usuario confirmó - delegar al handler principal
                delete_handler = DeleteBookIntentHandler()
                return delete_handler.handle(handler_input)
            else:
                # Usuario canceló
                session_attrs.pop("confirming_delete", None)
                session_attrs.pop("delete_book_title", None)
                
                speak_output = f"De acuerdo, no eliminaré '{book_title}'. "
                speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
                ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
                
                return (
                    handler_input.response_builder
                        .speak(speak_output)
                        .ask(ask_output)
                        .response
                )
                
        except Exception as e:
            logger.error(f"Error en ConfirmDeleteHandler: {e}", exc_info=True)
            
            # Limpiar sesión y respuesta de error
            session_attrs = handler_input.attributes_manager.session_attributes
            session_attrs.pop("confirming_delete", None)
            session_attrs.pop("delete_book_title", None)
            
            speak_output = "Hubo un problema. ¿Qué te gustaría hacer?"
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(ask_output)
                    .response
            )