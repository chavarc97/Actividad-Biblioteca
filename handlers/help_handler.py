"""
Handler para proporcionar ayuda al usuario
"""
import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response


logger = logging.getLogger(__name__)


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