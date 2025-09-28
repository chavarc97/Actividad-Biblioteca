"""
Handlers de Alexa para la skill de Biblioteca
Aplican SOLID: cada handler traduce Alexa ↔ Servicios (SRP)
Los servicios se obtienen vía ServiceFactory (DIP)
"""
import logging
from typing import Optional, List

import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response

from factories.service_factory import get_service_factory, DatabaseManager
from helpers.phrases import SALUDOS, OPCIONES_MENU, PREGUNTAS_QUE_HACER, ALGO_MAS, CONFIRMACIONES
from helpers.utils import IdGenerator

logger = logging.getLogger(__name__)

def _user_id(handler_input) -> str:
    return handler_input.request_envelope.context.system.user.user_id

def _slot(handler_input, name: str) -> Optional[str]:
    try:
        return ask_utils.get_slot_value(handler_input, name)
    except Exception:
        return None

def _choose(arr: List[str]) -> str:
    try:
        return IdGenerator.choose_random(arr)
    except Exception:
        import random
        return random.choice(arr)

class AyudaHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input) or ask_utils.is_intent_name("AyudaIntent")(handler_input)

    def handle(self, handler_input):
        speak = "Puedo ayudarte a agregar, listar, buscar, prestar y devolver libros. "                 "Por ejemplo, di: agrega el libro Cien años de soledad; o: préstame El principito a Ana; "                 "o: lista mis libros disponibles. " + _choose(PREGUNTAS_QUE_HACER)
        return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
