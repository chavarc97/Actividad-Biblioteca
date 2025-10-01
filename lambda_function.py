"""
Función Lambda principal refactorizada
Aplica principios SOLID y arquitectura por capas
"""
import os
import logging
from typing import Dict, Any

from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
import ask_sdk_core.utils as ask_utils

# Importar handlers refactorizados
from handlers.add_book_handler import AddBookIntentHandler, ContinueAddingBookHandler
from handlers.launch_handler import LaunchRequestHandler
from handlers.list_books_handler import ListBooksIntentHandler
from handlers.delete_book_handler import DeleteBookIntentHandler
from handlers.loan_handler import LoanBookIntentHandler, ReturnBookIntentHandler
from handlers.search_and_query_handlers import BuscarLibroIntentHandler, ConsultarDevueltosIntentHandler, MostrarOpcionesIntentHandler, LimpiarCacheIntentHandler
from handlers.help_handler import HelpIntentHandler
from handlers.fallback_handler import FallbackIntentHandler
from handlers.session_handlers import CancelOrStopIntentHandler, SessionEndedRequestHandler

# Importar factory y servicios
from factories.service_factory import get_service_factory
from helpers.utils import ResponsePhrases

# Configurar logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Configuración desde variables de entorno
USE_FAKE_S3 = os.getenv("USE_FAKE_S3", "false").lower() == "true"
S3_BUCKET = os.environ.get("S3_PERSISTENCE_BUCKET")

# Validar configuración
if not USE_FAKE_S3 and not S3_BUCKET:
    raise RuntimeError("S3_PERSISTENCE_BUCKET es requerido cuando USE_FAKE_S3=false")

logger.info(f"Lambda initialized - USE_FAKE_S3: {USE_FAKE_S3}")

# Obtener factory global
service_factory = get_service_factory()

# Crear skill builder con adaptador apropiado
data_adapter = service_factory.get_data_adapter()
sb = CustomSkillBuilder(persistence_adapter=data_adapter)


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """
    Maneja todas las excepciones no capturadas
    
    Principios aplicados:
    - Single Responsibility: Solo manejo de excepciones globales
    - Fail Fast: Registra errores y proporciona respuesta de respaldo
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
        logger.error(f"Unhandled exception: {exception}", exc_info=True)
        
        # Limpiar sesión en caso de error crítico
        try:
            handler_input.attributes_manager.session_attributes = {}
        except Exception as cleanup_error:
            logger.error(f"Error during session cleanup: {cleanup_error}")
        
        # Respuestas de error variadas
        error_responses = [
            "Ups, algo no salió como esperaba. ¿Podemos intentarlo de nuevo?",
            "Perdón, tuve un pequeño problema. ¿Lo intentamos otra vez?",
            "Disculpa, hubo un inconveniente técnico. ¿Qué querías hacer?",
            "Lo siento, algo falló. Empecemos de nuevo, ¿qué necesitas?"
        ]
        
        speak_output = ResponsePhrases.get_random_phrase(error_responses)
        ask_output = "¿En qué puedo ayudarte?"
        
        return (
            handler_input.response_builder
                .speak(speak_output)
                .ask(ask_output)
                .response
        )


# ==============================
# Registro de handlers en orden de prioridad
# ==============================

# Handlers de request principal
sb.add_request_handler(LaunchRequestHandler())

# Handlers de diálogo - ORDEN CRÍTICO
# ContinueAddingBookHandler DEBE ir ANTES para interceptar respuestas durante diálogo
sb.add_request_handler(ContinueAddingBookHandler())
sb.add_request_handler(AddBookIntentHandler())

# Handlers de funcionalidad principal
sb.add_request_handler(ListBooksIntentHandler())
sb.add_request_handler(DeleteBookIntentHandler())  # Funcionalidad nueva
sb.add_request_handler(LoanBookIntentHandler())
sb.add_request_handler(ReturnBookIntentHandler())
sb.add_request_handler(BuscarLibroIntentHandler())
sb.add_request_handler(ConsultarDevueltosIntentHandler())
sb.add_request_handler(MostrarOpcionesIntentHandler())
sb.add_request_handler(LimpiarCacheIntentHandler())

# Handlers de navegación y ayuda
sb.add_request_handler(HelpIntentHandler())

# Handlers de sistema (orden importante)
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())  # Debe ir hacia el final
sb.add_request_handler(SessionEndedRequestHandler())  # Debe ir al final

# Handler de excepciones global
sb.add_exception_handler(CatchAllExceptionHandler())

# ==============================
# Función Lambda principal
# ==============================

def lambda_handler(event, context):
    """
    Función principal de AWS Lambda
    
    Args:
        event: Evento de Alexa
        context: Contexto de Lambda
    
    Returns:
        Response de Alexa
    """
    try:
        logger.info(f"Lambda invoked with event: {event.get('request', {}).get('type', 'Unknown')}")
        
        # Procesar request usando skill builder
        return sb.lambda_handler()(event, context)
        
    except Exception as e:
        logger.error(f"Critical error in lambda_handler: {e}", exc_info=True)
        
        # Respuesta de emergencia si todo falla
        return {
            'version': '1.0',
            'response': {
                'outputSpeech': {
                    'type': 'PlainText',
                    'text': 'Lo siento, hubo un problema técnico. Por favor, intenta de nuevo más tarde.'
                },
                'shouldEndSession': True
            }
        }


# ==============================
# Función para testing local
# ==============================

def test_lambda_locally():
    """
    Función para probar el lambda localmente
    Útil para desarrollo y debugging
    """
    # Configurar para testing
    os.environ["USE_FAKE_S3"] = "true"
    service_factory.configure_for_testing(use_fake_s3=True, enable_cache=False)
    
    # Evento de prueba - LaunchRequest
    test_event = {
        "version": "1.0",
        "session": {
            "new": True,
            "sessionId": "amzn1.echo-api.session.test",
            "application": {"applicationId": "amzn1.ask.skill.test"},
            "user": {"userId": "amzn1.ask.account.test"}
        },
        "context": {
            "System": {
                "application": {"applicationId": "amzn1.ask.skill.test"},
                "user": {"userId": "amzn1.ask.account.test"},
                "device": {"deviceId": "test-device"}
            }
        },
        "request": {
            "type": "LaunchRequest",
            "requestId": "amzn1.echo-api.request.test",
            "timestamp": "2025-09-22T12:00:00Z"
        }
    }
    
    # Ejecutar lambda
    try:
        response = lambda_handler(test_event, None)
        print("Test response:")
        print(response.get('response', {}).get('outputSpeech', {}).get('text', 'No text'))
        return response
    except Exception as e:
        print(f"Test failed: {e}")
        return None


if __name__ == "__main__":
    # Ejecutar test si se ejecuta directamente
    test_lambda_locally()