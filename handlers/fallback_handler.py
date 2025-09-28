
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

class FallbackHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        sa = handler_input.attributes_manager.session_attributes
        if sa.get("agregando_libro"):
            esperando = sa.get("esperando")
            if esperando == "titulo":
                return handler_input.response_builder.speak("No entendí el título. Dime: el título es ...").ask("¿Cuál es el título?").response
            if esperando == "autor":
                return handler_input.response_builder.speak("No entendí el autor. Puedes decir: no sé.").ask("¿Quién es el autor?").response
            if esperando == "tipo":
                return handler_input.response_builder.speak("No entendí el tipo o género. Puedes decir: no sé.").ask("¿De qué tipo es el libro?").response
        speak = "Perdón, no entendí eso. " + _choose(PREGUNTAS_QUE_HACER)
        return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
