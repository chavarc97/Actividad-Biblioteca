
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

from services.book_service import BookService

class EliminarLibroHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("EliminarLibroIntent")(handler_input)

    def handle(self, handler_input):
        try:
            titulo = _slot(handler_input, "titulo")
            book_id = _slot(handler_input, "id_libro")
            if not titulo and not book_id:
                return handler_input.response_builder.speak("¿Cuál libro quieres eliminar? Puedes decir el título.").ask("Dime el título del libro que quieres borrar.").response

            service = self.factory.get_book_service(handler_input)
            ok, msg, book = service.delete_book(_user_id(handler_input), book_id=book_id, title=titulo)
            if not ok:
                return handler_input.response_builder.speak(msg).ask("¿Quieres eliminar otro libro?").response
            speak = msg + " " + _choose(ALGO_MAS)
            return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en EliminarLibroHandler")
            return handler_input.response_builder.speak("No pude eliminar el libro. Verifica el título e inténtalo de nuevo.").ask(_choose(PREGUNTAS_QUE_HACER)).response
