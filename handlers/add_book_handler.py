"""
Handler para agregar libros con diálogo conversacional
Aplica principios SOLID y maneja el flujo de conversación
"""
import logging
from typing import Optional

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response

from services.book_service import BookService
from helpers.utils import ResponsePhrases, ValidationUtils
from factories.service_factory import ServiceFactory


logger = logging.getLogger(__name__)


class AddBookIntentHandler(AbstractRequestHandler):
    """
    Handler para el intent de agregar libros
    
    Principios aplicados:
    - Single Responsibility: Solo maneja el intent de agregar libros
    - Dependency Inversion: Depende de abstracciones (BookService)
    """
    
    def __init__(self):
        """Constructor del handler"""
        self._service_factory = ServiceFactory()
    
    def can_handle(self, handler_input) -> bool:
        """
        Verifica si puede manejar la request
        
        Args:
            handler_input: Input del handler
        
        Returns:
            True si puede manejar la request
        """
        return ask_utils.is_intent_name("AgregarLibroIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el intent de agregar libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de Alexa
        """
        try:
            # Obtener servicios
            book_service = self._service_factory.get_book_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener valores de slots
            titulo = ask_utils.get_slot_value(handler_input, "titulo")
            autor = ask_utils.get_slot_value(handler_input, "autor")
            tipo = ask_utils.get_slot_value(handler_input, "tipo")
            
            session_attrs = handler_input.attributes_manager.session_attributes
            
            logger.info(f"AddBook - Título: {titulo}, Autor: {autor}, Tipo: {tipo}")
            
            # Recuperar valores de sesión si existen
            if session_attrs.get("agregando_libro"):
                titulo = titulo or session_attrs.get("titulo_temp")
                autor = autor or session_attrs.get("autor_temp")
                tipo = tipo or session_attrs.get("tipo_temp")
            
            # PASO 1: Solicitar título si no está presente
            if not titulo:
                return self._request_title(handler_input)
            
            # Validar título
            is_valid, error_msg = ValidationUtils.validate_book_title(titulo)
            if not is_valid:
                return self._handle_validation_error(handler_input, error_msg)
            
            # Guardar título en sesión
            session_attrs["titulo_temp"] = titulo
            session_attrs["agregando_libro"] = True
            
            # PASO 2: Solicitar autor si no está presente
            if not autor:
                return self._request_author(handler_input, titulo)
            
            # Validar autor
            is_valid, error_msg = ValidationUtils.validate_author_name(autor)
            if not is_valid:
                return self._handle_validation_error(handler_input, error_msg)
            
            # Normalizar autor
            if autor.lower() in ["no sé", "no se", "no lo sé"]:
                autor = "Desconocido"
            
            # Guardar autor en sesión
            session_attrs["autor_temp"] = autor
            
            # PASO 3: Solicitar tipo si no está presente
            if not tipo:
                return self._request_type(handler_input, titulo, autor)
            
            # Normalizar tipo
            if tipo.lower() in ["no sé", "no se", "no lo sé"]:
                tipo = "Sin categoría"
            
            # PASO 4: Crear el libro
            return self._create_book(handler_input, book_service, user_id, titulo, autor, tipo)
            
        except Exception as e:
            logger.error(f"Error en AddBookHandler: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _request_title(self, handler_input) -> Response:
        """
        Solicita el título del libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response solicitando título
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs["agregando_libro"] = True
        session_attrs["esperando"] = "titulo"
        
        speak_output = "¡Perfecto! Vamos a agregar un libro. ¿Cuál es el título?"
        ask_output = "¿Cuál es el título del libro?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _request_author(self, handler_input, titulo: str) -> Response:
        """
        Solicita el autor del libro
        
        Args:
            handler_input: Input del handler
            titulo: Título del libro
        
        Returns:
            Response solicitando autor
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs["esperando"] = "autor"
        
        speak_output = f"¡'{titulo}' suena interesante! ¿Quién es el autor? Si no lo sabes, di: no sé."
        ask_output = "¿Quién es el autor? Puedes decir 'no sé el autor' si no lo conoces."
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _request_type(self, handler_input, titulo: str, autor: str) -> Response:
        """
        Solicita el tipo/género del libro
        
        Args:
            handler_input: Input del handler
            titulo: Título del libro
            autor: Autor del libro
        
        Returns:
            Response solicitando tipo
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        session_attrs["esperando"] = "tipo"
        
        autor_text = f" de {autor}" if autor != "Desconocido" else ""
        speak_output = f"Casi listo con '{titulo}'{autor_text}. ¿De qué tipo o género es? Por ejemplo: novela, fantasía, historia. Si no sabes, di: no sé."
        ask_output = "¿De qué tipo es el libro? Puedes decir 'no sé el tipo' si no lo sabes."
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _create_book(self, handler_input, book_service: BookService, user_id: str, 
                    titulo: str, autor: str, tipo: str) -> Response:
        """
        Crea el libro con todos los datos recolectados
        
        Args:
            handler_input: Input del handler
            book_service: Servicio de libros
            user_id: ID del usuario
            titulo: Título del libro
            autor: Autor del libro
            tipo: Tipo del libro
        
        Returns:
            Response confirmando creación
        """
        # Crear el libro usando el servicio
        success, message, book = book_service.add_book(user_id, titulo, autor, tipo)
        
        # Limpiar sesión
        handler_input.attributes_manager.session_attributes = {}
        
        if success:
            # Obtener estadísticas actualizadas
            stats = book_service.get_book_statistics(user_id)
            total_books = stats["total_books"]
            
            # Construir respuesta de éxito
            confirmacion = ResponsePhrases.get_random_phrase(ResponsePhrases.CONFIRMACIONES)
            speak_output = f"{confirmacion} He agregado '{titulo}'"
            
            if autor != "Desconocido":
                speak_output += f" de {autor}"
            
            if tipo != "Sin categoría":
                speak_output += f", categoría {tipo}"
            
            speak_output += f". Ahora tienes {total_books} "
            speak_output += "libro" if total_books == 1 else "libros"
            speak_output += " en tu biblioteca. "
            
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
        else:
            # Manejar error del servicio
            speak_output = f"Ups, {message}. "
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_validation_error(self, handler_input, error_message: str) -> Response:
        """
        Maneja errores de validación
        
        Args:
            handler_input: Input del handler
            error_message: Mensaje de error
        
        Returns:
            Response con mensaje de error
        """
        speak_output = f"Hubo un problema: {error_message}. Intentemos de nuevo."
        ask_output = "¿Qué libro quieres agregar?"
        
        # Limpiar sesión en caso de error
        handler_input.attributes_manager.session_attributes = {}
        
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
            Response genérica de error
        """
        # Limpiar sesión en caso de error
        handler_input.attributes_manager.session_attributes = {}
        
        speak_output = "Hubo un problema agregando el libro. Intentemos de nuevo."
        ask_output = "¿Qué libro quieres agregar?"
        
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


class ContinueAddingBookHandler(AbstractRequestHandler):
    """
    Handler para continuar el proceso de agregar libro
    Maneja las respuestas del usuario durante el diálogo multi-turno
    """
    
    def __init__(self):
        """Constructor del handler"""
        self._service_factory = ServiceFactory()
    
    def can_handle(self, handler_input) -> bool:
        """
        Verifica si puede manejar la request
        Solo aplica si estamos en proceso de agregar libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            True si puede manejar la request
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        
        # Solo manejar si estamos agregando Y no es el intent principal
        return (session_attrs.get("agregando_libro") and 
                not ask_utils.is_intent_name("AgregarLibroIntent")(handler_input) and
                not ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) and
                not ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))
    
    def handle(self, handler_input) -> Response:
        """
        Continúa el proceso de agregar libro basado en lo que estamos esperando
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response apropiada según el paso actual
        """
        try:
            session_attrs = handler_input.attributes_manager.session_attributes
            esperando = session_attrs.get("esperando")
            
            # Obtener el valor de la respuesta del usuario
            valor = self._extract_user_response(handler_input)
            
            logger.info(f"ContinueAdding - Esperando: {esperando}, Valor: {valor}")
            
            # Procesar según lo que estamos esperando
            if esperando == "titulo":
                return self._process_title_response(handler_input, valor)
            elif esperando == "autor":
                return self._process_author_response(handler_input, valor)
            elif esperando == "tipo":
                return self._process_type_response(handler_input, valor)
            else:
                # Estado inválido, reiniciar
                return self._restart_process(handler_input)
                
        except Exception as e:
            logger.error(f"Error en ContinueAddingBookHandler: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _extract_user_response(self, handler_input) -> Optional[str]:
        """
        Extrae la respuesta del usuario de diferentes fuentes
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Respuesta del usuario o None
        """
        request = handler_input.request_envelope.request
        
        if hasattr(request, 'intent') and request.intent:
            intent_name = getattr(request.intent, 'name', None)
            
            # Buscar en el slot 'respuesta' del RespuestaGeneralIntent
            if intent_name == "RespuestaGeneralIntent":
                return ask_utils.get_slot_value(handler_input, "respuesta")
            
            # Buscar en cualquier slot disponible
            if hasattr(request.intent, 'slots') and request.intent.slots:
                for slot_name, slot in request.intent.slots.items():
                    if slot and hasattr(slot, 'value') and slot.value:
                        return slot.value
        
        return None
    
    def _process_title_response(self, handler_input, valor: Optional[str]) -> Response:
        """
        Procesa la respuesta del título
        
        Args:
            handler_input: Input del handler
            valor: Valor capturado
        
        Returns:
            Response apropiada
        """
        if valor:
            # Validar título
            is_valid, error_msg = ValidationUtils.validate_book_title(valor)
            if not is_valid:
                return self._handle_validation_error(handler_input, error_msg)
            
            session_attrs = handler_input.attributes_manager.session_attributes
            session_attrs["titulo_temp"] = valor
            session_attrs["esperando"] = "autor"
            
            speak_output = f"¡'{valor}' suena interesante! ¿Quién es el autor? Si no lo sabes, di: no sé el autor."
            ask_output = "¿Quién es el autor? Puedes decir 'el autor es' y el nombre, o 'no sé el autor'."
            
        else:
            speak_output = "No entendí el título. Por favor di: 'el título es' seguido del nombre del libro."
            ask_output = "¿Cuál es el título del libro?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _process_author_response(self, handler_input, valor: Optional[str]) -> Response:
        """
        Procesa la respuesta del autor
        
        Args:
            handler_input: Input del handler
            valor: Valor capturado
        
        Returns:
            Response apropiada
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        
        # Manejar "no sé"
        if not valor or valor.lower() in ["no sé", "no se", "no lo sé", "no lo se", 
                                          "no sé el autor", "no se el autor"]:
            valor = "Desconocido"
        else:
            # Limpiar prefijos comunes
            if valor.lower().startswith("el autor es "):
                valor = valor[12:].strip()
            elif valor.lower().startswith("es "):
                valor = valor[3:].strip()
        
        session_attrs["autor_temp"] = valor
        session_attrs["esperando"] = "tipo"
        
        titulo = session_attrs.get("titulo_temp")
        autor_text = f" de {valor}" if valor != "Desconocido" else ""
        
        speak_output = f"Perfecto, '{titulo}'{autor_text}. ¿De qué tipo o género es? Por ejemplo: novela, fantasía, ciencia ficción. Si no sabes, di: no sé el tipo."
        ask_output = "¿De qué tipo es el libro? Puedes decir 'el tipo es' y el género, o 'no sé el tipo'."
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _process_type_response(self, handler_input, valor: Optional[str]) -> Response:
        """
        Procesa la respuesta del tipo y crea el libro
        
        Args:
            handler_input: Input del handler
            valor: Valor capturado
        
        Returns:
            Response final creando el libro
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        
        # Manejar "no sé"
        if not valor or valor.lower() in ["no sé", "no se", "no lo sé", "no lo se",
                                          "no sé el tipo", "no se el tipo"]:
            valor = "Sin categoría"
        else:
            # Limpiar prefijos comunes
            if valor.lower().startswith("el tipo es "):
                valor = valor[11:].strip()
            elif valor.lower().startswith("es "):
                valor = valor[3:].strip()
        
        # Obtener datos completos y crear libro
        titulo_final = session_attrs.get("titulo_temp")
        autor_final = session_attrs.get("autor_temp", "Desconocido")
        tipo_final = valor
        
        # Usar el servicio para crear el libro
        book_service = self._service_factory.get_book_service(handler_input)
        user_id = handler_input.request_envelope.context.system.user.user_id
        
        success, message, book = book_service.add_book(user_id, titulo_final, autor_final, tipo_final)
        
        # Limpiar sesión
        handler_input.attributes_manager.session_attributes = {}
        
        if success:
            stats = book_service.get_book_statistics(user_id)
            total_books = stats["total_books"]
            
            confirmacion = ResponsePhrases.get_random_phrase(ResponsePhrases.CONFIRMACIONES)
            speak_output = f"{confirmacion} He agregado '{titulo_final}'"
            
            if autor_final != "Desconocido":
                speak_output += f" de {autor_final}"
            
            if tipo_final != "Sin categoría":
                speak_output += f", categoría {tipo_final}"
            
            speak_output += f". Ahora tienes {total_books} "
            speak_output += "libro" if total_books == 1 else "libros"
            speak_output += " en tu biblioteca. "
            
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        else:
            speak_output = f"Ups, {message}. "
            speak_output += ResponsePhrases.get_random_phrase(ResponsePhrases.ALGO_MAS)
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _restart_process(self, handler_input) -> Response:
        """
        Reinicia el proceso de agregar libro
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response reiniciando el proceso
        """
        handler_input.attributes_manager.session_attributes = {}
        
        speak_output = "Hubo un problema. Empecemos de nuevo. ¿Qué libro quieres agregar?"
        ask_output = "¿Qué libro quieres agregar?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )
    
    def _handle_validation_error(self, handler_input, error_message: str) -> Response:
        """
        Maneja errores de validación durante el diálogo
        
        Args:
            handler_input: Input del handler
            error_message: Mensaje de error
        
        Returns:
            Response con mensaje de error
        """
        speak_output = f"Hubo un problema: {error_message}. Intentemos de nuevo."
        
        session_attrs = handler_input.attributes_manager.session_attributes
        esperando = session_attrs.get("esperando")
        
        if esperando == "titulo":
            ask_output = "¿Cuál es el título del libro?"
        elif esperando == "autor":
            ask_output = "¿Quién es el autor?"
        elif esperando == "tipo":
            ask_output = "¿De qué tipo es el libro?"
        else:
            ask_output = "¿Qué libro quieres agregar?"
            handler_input.attributes_manager.session_attributes = {}
        
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
            Response genérica de error
        """
        handler_input.attributes_manager.session_attributes = {}
        
        speak_output = "Hubo un problema. Intentemos agregar el libro de nuevo."
        ask_output = "¿Qué libro quieres agregar?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )