"""
Handlers de Launch y handlers de sistema (Help, Fallback, Cancel/Stop, Session)
Basado en el código original pero refactorizado con principios SOLID
"""
import logging
import random

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_model import Response

from services.book_service import BookService
from services.loan_service import LoanService
from helpers.utils import ResponsePhrases, TextUtils
from factories.service_factory import DatabaseManager, get_service_factory


logger = logging.getLogger(__name__)


# ==========================================
# LAUNCH REQUEST HANDLER
# ==========================================

class LaunchRequestHandler(AbstractRequestHandler):
    """
    Handler para cuando el usuario abre la skill (LaunchRequest)
    
    Principios aplicados:
    - Single Responsibility: Solo maneja el inicio de la skill
    - Open/Closed: Extensible para diferentes tipos de bienvenida
    """
    
    def __init__(self):
        """Constructor del handler"""
        self.service_factory = get_service_factory()
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el LaunchRequest con saludo personalizado
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de bienvenida
        """
        try:
            # Limpiar sesión al inicio
            handler_input.attributes_manager.session_attributes = {}
            
            # Obtener servicios
            book_service = self.service_factory.get_book_service(handler_input)
            loan_service = self.service_factory.get_loan_service(handler_input)
            user_id = self._extract_user_id(handler_input)
            
            # Obtener y sincronizar datos del usuario
            user_data = DatabaseManager.get_user_data(handler_input)
            
            # Registrar inicio de sesión
            historial = user_data.setdefault("historial_conversaciones", [])
            historial.append({
                "tipo": "inicio_sesion",
                "timestamp": self._get_timestamp(),
                "accion": "bienvenida"
            })
            DatabaseManager.save_user_data(handler_input, user_data)
            
            # Obtener estadísticas
            stats = book_service.get_book_statistics(user_id)
            total_libros = stats["total_books"]
            active_loans = loan_service.get_active_loans(user_id)
            prestamos_activos = len(active_loans)
            
            # Determinar si es usuario frecuente
            es_usuario_frecuente = len(historial) > 5
            
            # Construir saludo personalizado
            speak_output = self._build_greeting(
                es_usuario_frecuente,
                total_libros,
                prestamos_activos
            )
            
            ask_output = ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
            
            return (
                handler_input.response_builder
                    .speak(speak_output)
                    .ask(ask_output)
                    .response
            )
            
        except Exception as e:
            logger.error(f"Error en LaunchRequest: {e}", exc_info=True)
            return self._handle_error(handler_input)
    
    def _build_greeting(self, es_usuario_frecuente: bool, total_libros: int, prestamos_activos: int) -> str:
        """
        Construye el saludo personalizado
        
        Args:
            es_usuario_frecuente: Si es usuario frecuente
            total_libros: Total de libros
            prestamos_activos: Préstamos activos
        
        Returns:
            Texto del saludo
        """
        # Saludo inicial
        if es_usuario_frecuente and total_libros > 0:
            saludo = "¡Hola de nuevo! ¡Qué bueno verte por aquí!"
            estado = f" Veo que tienes {total_libros} "
            estado += TextUtils.pluralize(total_libros, "libro", "libros")
            estado += " en tu biblioteca"
            
            if prestamos_activos > 0:
                estado += f" y {prestamos_activos} "
                estado += TextUtils.pluralize(prestamos_activos, "préstamo activo", "préstamos activos")
            estado += "."
        else:
            saludo = ResponsePhrases.get_random_phrase(ResponsePhrases.SALUDOS)
            
            if total_libros == 0:
                estado = " Veo que es tu primera vez aquí. ¡Empecemos a construir tu biblioteca!"
            else:
                estado = f" Tienes {total_libros} "
                estado += TextUtils.pluralize(total_libros, "libro", "libros")
                estado += " en tu colección."
        
        # Opciones disponibles
        opciones = " " + ResponsePhrases.get_random_phrase(ResponsePhrases.OPCIONES_MENU)
        
        # Pregunta final
        pregunta = " " + ResponsePhrases.get_random_phrase(ResponsePhrases.PREGUNTAS_QUE_HACER)
        
        return saludo + estado + opciones + pregunta
    
    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual en formato ISO"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _handle_error(self, handler_input) -> Response:
        """Maneja errores en el launch"""
        speak_output = "¡Hola! Bienvenido a tu biblioteca. ¿En qué puedo ayudarte?"
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


# ==========================================
# HELP HANDLER
# ==========================================

class HelpIntentHandler(AbstractRequestHandler):
    """
    Handler para el intent de ayuda (AMAZON.HelpIntent)
    """
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Proporciona ayuda al usuario
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response con ayuda
        """
        speak_output = (
            "¡Por supuesto! Te explico cómo funciona tu biblioteca. "
            "Puedes agregar libros nuevos diciendo 'agrega un libro', "
            "ver todos tus libros con 'lista mis libros', "
            "buscar un libro específico con 'busca' y el título, "
            "prestar un libro diciendo 'presta' seguido del título, "
            "registrar devoluciones con 'devuelvo' y el título, "
            "eliminar libros con 'elimina' y el título, "
            "o consultar tus préstamos activos preguntando 'qué libros tengo prestados'. "
            "¿Qué te gustaría hacer primero?"
        )
        
        ask_output = "¿Con qué te ayudo?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )


# ==========================================
# CANCEL / STOP HANDLER
# ==========================================

class CancelStopIntentHandler(AbstractRequestHandler):
    """
    Handler para cancelar o detener (AMAZON.CancelIntent y AMAZON.StopIntent)
    """
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))
    
    def handle(self, handler_input) -> Response:
        """
        Maneja la cancelación o detención de la skill
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de despedida
        """
        # Limpiar sesión al salir
        handler_input.attributes_manager.session_attributes = {}
        
        speak_output = ResponsePhrases.get_random_phrase(ResponsePhrases.DESPEDIDAS)
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .response
        )


# ==========================================
# SESSION ENDED HANDLER
# ==========================================

class SessionEndedRequestHandler(AbstractRequestHandler):
    """
    Handler para cuando la sesión termina (SessionEndedRequest)
    """
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja el fin de sesión
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response vacía
        """
        # Limpiar sesión
        try:
            handler_input.attributes_manager.session_attributes = {}
            
            # Log de la razón del fin de sesión (para debugging)
            request = handler_input.request_envelope.request
            if hasattr(request, 'reason'):
                logger.info(f"Session ended. Reason: {request.reason}")
            if hasattr(request, 'error'):
                logger.error(f"Session ended with error: {request.error}")
        except Exception as e:
            logger.error(f"Error handling session end: {e}")
        
        return handler_input.response_builder.response


# ==========================================
# FALLBACK HANDLER
# ==========================================

class FallbackIntentHandler(AbstractRequestHandler):
    """
    Handler para cuando Alexa no entiende el comando (AMAZON.FallbackIntent)
    """
    
    def can_handle(self, handler_input) -> bool:
        """Verifica si puede manejar la request"""
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)
    
    def handle(self, handler_input) -> Response:
        """
        Maneja comandos no entendidos
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Response de fallback
        """
        session_attrs = handler_input.attributes_manager.session_attributes
        
        # Si estamos agregando un libro, manejar respuestas
        if session_attrs.get("agregando_libro"):
            esperando = session_attrs.get("esperando")
            
            if esperando == "titulo":
                speak_output = "No entendí el título. Por favor di: 'el título es' seguido del nombre del libro."
                ask_output = "¿Cuál es el título del libro?"
            elif esperando == "autor":
                speak_output = "No entendí el autor. Por favor di: 'el autor es' seguido del nombre, o di: no sé el autor."
                ask_output = "¿Quién es el autor? Puedes decir: 'no sé el autor'."
            elif esperando == "tipo":
                speak_output = "No entendí el tipo. Por favor di: 'el tipo es' seguido del género, o di: no sé el tipo."
                ask_output = "¿De qué tipo es el libro? Puedes decir: 'no sé el tipo'."
            else:
                speak_output = "No entendí eso. Intentemos agregar el libro de nuevo."
                ask_output = "¿Qué libro quieres agregar?"
                session_attrs.clear()
        
        # Si estamos listando libros con paginación
        elif session_attrs.get("listando_libros"):
            speak_output = "No entendí eso. ¿Quieres ver más libros? Di 'siguiente' para continuar o 'salir' para terminar."
            ask_output = "Di 'siguiente' o 'salir'."
        
        # Comportamiento normal del fallback
        else:
            respuestas = [
                "Disculpa, no entendí eso. ¿Podrías repetirlo de otra forma?",
                "Hmm, no estoy seguro de qué quisiste decir. ¿Me lo puedes decir de otra manera?",
                "Perdón, no comprendí. ¿Puedes intentarlo de nuevo?"
            ]
            
            speak_output = random.choice(respuestas)
            speak_output += " Recuerda que puedo ayudarte a agregar libros, listarlos, prestarlos, eliminarlos o registrar devoluciones."
            ask_output = "¿Qué te gustaría hacer?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )


# ==========================================
# EXCEPTION HANDLER
# ==========================================

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """
    Maneja todas las excepciones no capturadas
    """
    
    def can_handle(self, handler_input, exception):
        """Puede manejar cualquier excepción"""
        return True
    
    def handle(self, handler_input, exception):
        """
        Maneja excepciones globales
        
        Args:
            handler_input: Input del handler
            exception: Excepción capturada
        
        Returns:
            Response de error amigable
        """
        logger.error(f"Exception: {exception}", exc_info=True)
        
        # Limpiar sesión en caso de error
        try:
            handler_input.attributes_manager.session_attributes = {}
        except Exception as cleanup_error:
            logger.error(f"Error during session cleanup: {cleanup_error}")
        
        # Respuestas de error variadas
        respuestas = [
            "Ups, algo no salió como esperaba. ¿Podemos intentarlo de nuevo?",
            "Perdón, tuve un pequeño problema. ¿Lo intentamos otra vez?",
            "Disculpa, hubo un inconveniente. ¿Qué querías hacer?"
        ]
        
        speak_output = random.choice(respuestas)
        ask_output = "¿En qué puedo ayudarte?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )