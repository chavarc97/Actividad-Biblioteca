"""
Handlers para búsqueda de libros y consulta de historial
Basado en el código original pero refactorizado con principios SOLID
"""
import logging
from typing import List

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response

from services.book_service import BookService
from services.loan_service import LoanService
from helpers.utils import ResponsePhrases, TextUtils
from factories.service_factory import get_service_factory


logger = logging.getLogger(__name__)


class BuscarLibroIntentHandler(AbstractRequestHandler):
    """
    Handler para buscar libros por título o autor
    
    Principios aplicados:
    - Single Responsibility: Solo búsqueda de libros
    - Open/Closed: Extensible para nuevos tipos de búsqueda
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
        return ask_utils.is_intent_name("BuscarLibroIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el intent de buscar libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            # Obtener servicios
            book_service = self.service_factory.get_book_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener criterios de búsqueda
            titulo = ask_utils.get_slot_value(handler_input, "titulo")
            autor = ask_utils.get_slot_value(handler_input, "autor")
            
            if not titulo and not autor:
                return self._request_search_criteria(handler_input)
            
            # Realizar búsqueda
            books_found = []
            search_type = ""
            search_term = ""
            
            if titulo:
                books_found = book_service.search_books_by_title(user_id, titulo)
                search_type = "título"
                search_term = titulo
            elif autor:
                books_found = book_service.search_books_by_author(user_id, autor)
                search_type = "autor"
                search_term = autor
            
            return self._handle_search_results(handler_input, books_found, search_type, search_term)
            
        except Exception as e:
            logger.error(f"Error en BuscarLibro: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _request_search_criteria(self, handler_input) -> Response:
        """
        Solicita criterios de búsqueda
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response solicitando criterios
        """
        speak_output = "¿Qué libro quieres buscar? Puedes decirme el título o el nombre del autor."
        ask_output = "Dime el título del libro o el nombre del autor que buscas."
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_search_results(self, handler_input, books_found: List, 
                              search_type: str, search_term: str) -> Response:
        """
        Maneja los resultados de búsqueda
        
        Args:
            handler_input: Input del handler
            books_found: Libros encontrados
            search_type: Tipo de búsqueda (título/autor)
            search_term: Término buscado
        
        Returns:
            Response con resultados
        """
        if not books_found:
            speak_output = f"No encontré ningún libro con {search_type} '{search_term}' en tu biblioteca. "
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        elif len(books_found) == 1:
            book = books_found[0]
            speak_output = f"Encontré '{book.titulo}'. "
            
            # Agregar detalles del libro
            details = []
            if book.autor != "Desconocido":
                details.append(f"Autor: {book.autor}")
            if book.tipo != "Sin categoría":
                details.append(f"Tipo: {book.tipo}")
            
            estado_text = "disponible" if book.esta_disponible() else "prestado"
            details.append(f"Estado: {estado_text}")
            
            if book.total_prestamos > 0:
                prestamos_text = TextUtils.pluralize(book.total_prestamos, "vez", "veces")
                details.append(f"Ha sido prestado {book.total_prestamos} {prestamos_text}")
            
            if details:
                speak_output += " ".join(details) + ". "
            
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        else:
            # Múltiples libros encontrados
            books_count = len(books_found)
            books_text = TextUtils.pluralize(books_count, "libro", "libros")
            speak_output = f"Encontré {books_count} {books_text} que coinciden con {search_type} '{search_term}': "
            
            # Mostrar hasta 3 libros con detalles
            book_descriptions = []
            for book in books_found[:3]:
                desc = f"'{book.titulo}'"
                if book.autor != "Desconocido":
                    desc += f" de {book.autor}"
                book_descriptions.append(desc)
            
            speak_output += TextUtils.format_list_natural(book_descriptions, "y")
            
            if len(books_found) > 3:
                speak_output += f" y {len(books_found) - 3} más"
            
            speak_output += ". " + ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_error(self, handler_input) -> Response:
        """Maneja errores generales"""
        speak_output = "Hubo un problema buscando el libro. ¿Intentamos de nuevo?"
        ask_output = "¿Qué libro buscas?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """Extrae el user ID"""
        return handler_input.request_envelope.context.system.user.user_id


class ConsultarDevueltosIntentHandler(AbstractRequestHandler):
    """
    Handler para consultar historial de devoluciones
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("ConsultarDevueltosIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja la consulta de historial de devoluciones
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            loan_service = self.service_factory.get_loan_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener historial completo
            all_loans = loan_service.get_loan_history(user_id)
            
            # Filtrar solo los devueltos
            returned_loans = [loan for loan in all_loans if loan.estado.value == "devuelto"]
            
            if not returned_loans:
                speak_output = "Aún no has registrado devoluciones. Cuando prestes libros y te los devuelvan, aparecerán aquí. "
                speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            else:
                total = len(returned_loans)
                returns_text = TextUtils.pluralize(total, "devolución", "devoluciones")
                speak_output = f"Has registrado {total} {returns_text} en total. "
                
                # Mostrar TODOS los títulos (o hasta un máximo razonable)
                if total <= 10:
                    speak_output += "Los libros devueltos son: "
                    detalles = []
                    for loan in returned_loans:
                        detalle = f"'{loan.titulo}'"
                        if loan.persona and loan.persona not in ['Alguien', 'un amigo']:
                            detalle += f" que prestaste a {loan.persona}"
                        detalles.append(detalle)
                    speak_output += TextUtils.format_list_natural(detalles, "y")
                    speak_output += ". "
                else:
                    # Si son muchos, mostrar los últimos 5
                    recientes = returned_loans[-5:]
                    speak_output += "Los 5 más recientes son: "
                    detalles = []
                    for loan in reversed(recientes):
                        detalle = f"'{loan.titulo}'"
                        if loan.persona and loan.persona not in ['Alguien', 'un amigo']:
                            detalle += f" a {loan.persona}"
                        detalles.append(detalle)
                    speak_output += TextUtils.format_list_natural(detalles, "y")
                    speak_output += ". "
                
                speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(ask_output)
                    .response
            )
            
        except Exception as e:
            logger.error(f"Error en ConsultarDevueltos: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _handle_error(self, handler_input) -> Response:
        """Maneja errores"""
        speak_output = "Hubo un problema consultando el historial."
        ask_output = "¿Qué más deseas hacer?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """Extrae el user ID"""
        return handler_input.request_envelope.context.system.user.user_id


class MostrarOpcionesIntentHandler(AbstractRequestHandler):
    """
    Handler para mostrar las opciones disponibles del menú
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("MostrarOpcionesIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Muestra las opciones del menú
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            book_service = self.service_factory.get_book_service(handler_input)
            loan_service = self.service_factory.get_loan_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener estadísticas del usuario
            stats = book_service.get_book_statistics(user_id)
            total_libros = stats["total_books"]
            active_loans = loan_service.get_active_loans(user_id)
            prestamos_activos = len(active_loans)
            
            intro = "¡Por supuesto! "
            opciones = ResponsePhrases.get_random_phrase(ResponsePhrases.OPCIONES_MENU)
            
            # Agregar contexto si es útil
            if total_libros == 0:
                contexto = " Como aún no tienes libros, te sugiero empezar agregando algunos."
            elif prestamos_activos > 0:
                prestamos_text = TextUtils.pluralize(prestamos_activos, "libro prestado", "libros prestados")
                contexto = f" Recuerda que tienes {prestamos_activos} {prestamos_text}."
            else:
                contexto = ""
            
            pregunta = " " + ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
            speak_output = intro + opciones + contexto + pregunta
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(ask_output)
                    .response
            )
            
        except Exception as e:
            logger.error(f"Error mostrando opciones: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _handle_error(self, handler_input) -> Response:
        """Maneja errores"""
        speak_output = "Puedo ayudarte a gestionar tu biblioteca. ¿Qué te gustaría hacer?"
        ask_output = "¿En qué puedo ayudarte?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """Extrae el user ID"""
        return handler_input.request_envelope.context.system.user.user_id


class LimpiarCacheIntentHandler(AbstractRequestHandler):
    """
    Handler para limpiar cache y sincronizar estados
    Útil para desarrollo y debugging
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("LimpiarCacheIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Limpia cache y sincroniza estados
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            user_id = self._extract_user_id(handler_input)
            
            # Limpiar cache del factory
            self.service_factory.reset_cache()
            
            # Limpiar sesión
            handler_input.attributes_manager.session_attributes = {}
            
            # Obtener datos sincronizados
            book_service = self.service_factory.get_book_service(handler_input)
            loan_service = self.service_factory.get_loan_service(handler_input)
            
            books = book_service.get_all_books(user_id)
            loans = loan_service.get_active_loans(user_id)
            
            speak_output = "He limpiado el cache y sincronizado tu biblioteca. "
            speak_output += f"Tienes {len(books)} "
            speak_output += TextUtils.pluralize(len(books), "libro", "libros")
            speak_output += " en total y "
            speak_output += f"{len(loans)} "
            speak_output += TextUtils.pluralize(len(loans), "préstamo activo", "préstamos activos")
            speak_output += ". "
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(ask_output)
                    .response
            )
            
        except Exception as e:
            logger.error(f"Error limpiando cache: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _handle_error(self, handler_input) -> Response:
        """Maneja errores"""
        speak_output = "Hubo un problema limpiando el cache. Intenta de nuevo."
        ask_output = "¿Qué deseas hacer?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _extract_user_id(self, handler_input) -> str:
        """Extrae el user ID"""
        return handler_input.request_envelope.context.system.user.user_id