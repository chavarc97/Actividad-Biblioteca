"""
Handler para listar libros con paginación y filtros
Basado en el código original pero refactorizado con principios SOLID
"""
import logging
from typing import List

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response

from services.book_service import BookService
from helpers.utils import ResponsePhrases, PaginationHelper, TextUtils
from factories.service_factory import get_service_factory


logger = logging.getLogger(__name__)


class ListBooksIntentHandler(AbstractRequestHandler):
    """
    Handler para el intent de listar libros con paginación
    
    Principios aplicados:
    - Single Responsibility: Solo maneja listado de libros
    - Dependency Inversion: Usa servicios abstractos
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
        self.pagination_helper = PaginationHelper(items_per_page=10)
    
    def can_handle(self, handler_input) -> bool:
        """
        Verifica si puede manejar la request
        
        Args:
            handler_input: Input del handler
        
        Returns:
            True si puede manejar la request
        """
        return ask_utils.is_intent_name("ListarLibrosIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el intent de listar libros
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            # Obtener servicios
            book_service = self.service_factory.get_book_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener parámetros de filtrado
            filtro = ask_utils.get_slot_value(handler_input, "filtro_tipo")
            autor = ask_utils.get_slot_value(handler_input, "autor")
            
            session_attrs = handler_input.attributes_manager.session_attributes
            
            # Obtener todos los libros
            todos_libros = book_service.get_all_books(user_id)
            
            if not todos_libros:
                return self._handle_no_books(handler_input)
            
            # Aplicar filtros
            libros_filtrados = self._apply_filters(book_service, user_id, todos_libros, filtro, autor)
            titulo_filtro = self._get_filter_title(filtro, autor)
            
            if not libros_filtrados:
                return self._handle_no_filtered_books(handler_input, titulo_filtro)
            
            # Manejar paginación
            return self._handle_pagination(handler_input, libros_filtrados, titulo_filtro, session_attrs)
            
        except Exception as e:
            logger.error(f"Error en ListBooksHandler: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _apply_filters(self, book_service: BookService, user_id: str, 
                      books: List, filtro: str, autor: str) -> List:
        """
        Aplica filtros a la lista de libros
        
        Args:
            book_service: Servicio de libros
            user_id: ID del usuario
            books: Lista de libros
            filtro: Filtro de tipo
            autor: Filtro de autor
        
        Returns:
            Lista filtrada de libros
        """
        libros_filtrados = books.copy()
        
        if autor:
            libros_filtrados = book_service.search_books_by_author(user_id, autor)
        elif filtro:
            if filtro.lower() in ["prestados", "prestado"]:
                libros_filtrados = book_service.get_loaned_books(user_id)
            elif filtro.lower() in ["disponibles", "disponible"]:
                libros_filtrados = book_service.get_available_books(user_id)
        
        return libros_filtrados
    
    def _get_filter_title(self, filtro: str, autor: str) -> str:
        """
        Obtiene el título del filtro aplicado
        
        Args:
            filtro: Filtro de tipo
            autor: Filtro de autor
        
        Returns:
            Título del filtro
        """
        if autor:
            return f" de {autor}"
        elif filtro:
            if filtro.lower() in ["prestados", "prestado"]:
                return " prestados"
            elif filtro.lower() in ["disponibles", "disponible"]:
                return " disponibles"
        return ""
    
    def _handle_no_books(self, handler_input) -> Response:
        """
        Maneja el caso cuando no hay libros
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response apropiada
        """
        speak_output = "Aún no tienes libros en tu biblioteca. ¿Te gustaría agregar el primero? Solo di: agrega un libro."
        ask_output = "¿Quieres agregar tu primer libro?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_no_filtered_books(self, handler_input, titulo_filtro: str) -> Response:
        """
        Maneja el caso cuando no hay libros que coincidan con el filtro
        
        Args:
            handler_input: Input del handler
            titulo_filtro: Título del filtro aplicado
        
        Returns:
            Response apropiada
        """
        speak_output = f"No encontré libros{titulo_filtro}. "
        speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
        ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_pagination(self, handler_input, libros_filtrados: List, 
                          titulo_filtro: str, session_attrs: dict) -> Response:
        """
        Maneja la paginación de libros
        
        Args:
            handler_input: Input del handler
            libros_filtrados: Lista de libros filtrados
            titulo_filtro: Título del filtro
            session_attrs: Atributos de sesión
        
        Returns:
            Response con paginación apropiada
        """
        # Si son 10 o menos, mostrar todos sin paginación
        if len(libros_filtrados) <= 10:
            return self._show_all_books(handler_input, libros_filtrados, titulo_filtro)
        
        # Paginación para más de 10 libros
        return self._show_paginated_books(handler_input, libros_filtrados, titulo_filtro, session_attrs)
    
    def _show_all_books(self, handler_input, books: List, titulo_filtro: str) -> Response:
        """
        Muestra todos los libros sin paginación
        
        Args:
            handler_input: Input del handler
            books: Lista de libros
            titulo_filtro: Título del filtro
        
        Returns:
            Response con todos los libros
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs["pagina_libros"] = 0
        session_attrs["listando_libros"] = False
        
        count_text = TextUtils.pluralize(len(books), "libro", "libros")
        speak_output = f"Tienes {len(books)} {count_text}{titulo_filtro}: "
        
        titulos = [f"'{book.titulo}'" for book in books]
        speak_output += TextUtils.format_list_natural(titulos, "y")
        speak_output += ". "
        speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
        
        ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _show_paginated_books(self, handler_input, books: List, 
                             titulo_filtro: str, session_attrs: dict) -> Response:
        """
        Muestra libros con paginación
        
        Args:
            handler_input: Input del handler
            books: Lista de libros
            titulo_filtro: Título del filtro
            session_attrs: Atributos de sesión
        
        Returns:
            Response con libros paginados
        """
        pagina_actual = session_attrs.get("pagina_libros", 0)
        pagination_info = self.pagination_helper.paginate(books, pagina_actual)
        
        libros_pagina = pagination_info["items"]
        
        # Construir mensaje
        if pagina_actual == 0:
            count_text = TextUtils.pluralize(len(books), "libro", "libros")
            speak_output = f"Tienes {len(books)} {count_text}{titulo_filtro}. "
            speak_output += f"Te los voy a mostrar de {self.pagination_helper.items_per_page} en {self.pagination_helper.items_per_page}. "
        else:
            speak_output = f"Página {pagina_actual + 1}. "
        
        speak_output += f"Libros del {pagination_info['start_index'] + 1} al {pagination_info['end_index']}: "
        
        titulos = [f"'{libro.titulo}'" for libro in libros_pagina]
        speak_output += TextUtils.format_list_natural(titulos, "y")
        speak_output += ". "
        
        if pagination_info["has_next"]:
            remaining = len(books) - pagination_info["end_index"]
            remaining_text = TextUtils.pluralize(remaining, "libro", "libros")
            speak_output += f"Quedan {remaining} {remaining_text} más. Di 'siguiente' para continuar o 'salir' para terminar."
            
            session_attrs["pagina_libros"] = pagina_actual + 1
            session_attrs["listando_libros"] = True
            session_attrs["libros_filtrados"] = [libro.to_dict() for libro in books]  # Serializar para sesión
            
            ask_output = "¿Quieres ver más libros? Di 'siguiente' o 'salir'."
        else:
            speak_output += "Esos son todos los libros. "
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            
            session_attrs["pagina_libros"] = 0
            session_attrs["listando_libros"] = False
            session_attrs.pop("libros_filtrados", None)
            
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
        handler_input.attributes_manager.session_attributes = {}
        
        speak_output = "Hubo un problema consultando tu biblioteca. ¿Intentamos de nuevo?"
        ask_output = "¿Qué te gustaría hacer?"
        
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


class SiguientePaginaIntentHandler(AbstractRequestHandler):
    """
    Handler para continuar con la siguiente página de libros
    """
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("SiguientePaginaIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Continúa con la paginación
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response con siguiente página
        """
        try:
            session_attrs = handler_input.attributes_manager.session_attributes
            
            if not session_attrs.get("listando_libros"):
                speak_output = "No estoy mostrando una lista en este momento. ¿Quieres ver tus libros?"
                ask_output = "¿Quieres que liste tus libros?"
                
                return (
                    handler_input.response_builder
                        .speak(speak_output)
                        .ask(ask_output)
                        .response
                )
            
            # Delegar al handler principal de listado
            list_handler = ListBooksIntentHandler()
            return list_handler.handle(handler_input)
            
        except Exception as e:
            logger.error(f"Error en SiguientePagina: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _handle_error(self, handler_input) -> Response:
        """Maneja errores"""
        handler_input.attributes_manager.session_attributes = {}
        
        speak_output = "Hubo un problema. ¿Qué te gustaría hacer?"
        ask_output = "¿En qué puedo ayudarte?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )


class SalirListadoIntentHandler(AbstractRequestHandler):
    """
    Handler para salir del listado paginado
    """
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("SalirListadoIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Sale del listado paginado
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response confirmando salida
        """
        # Limpiar estado de paginación
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs["pagina_libros"] = 0
        session_attrs["listando_libros"] = False
        session_attrs.pop("libros_filtrados", None)
        
        speak_output = "De acuerdo, terminé de mostrar los libros. "
        speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
        ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )