
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

class BuscarLibroHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("BuscarLibroIntent")(handler_input)

    def handle(self, handler_input):
        try:
            titulo = _slot(handler_input, "titulo")
            if not titulo:
                return handler_input.response_builder.speak("¿Qué libro quieres buscar?").ask("Dime el título del libro que buscas.").response

            service = self.factory.get_book_service(handler_input)
            user_id = _user_id(handler_input)
            encontrados = service.search_books_by_title(user_id, titulo.strip()) or []

            if not encontrados:
                return handler_input.response_builder.speak(f"No encontré ningún libro con el título '{titulo}'. " + _choose(ALGO_MAS)).ask(_choose(PREGUNTAS_QUE_HACER)).response
            if len(encontrados) == 1:
                b = encontrados[0]
                speak = f"Encontré '{b.titulo}'. Autor: {b.autor or 'Desconocido'}. Tipo: {b.tipo or 'Sin categoría'}. Estado: {b.estado.value}. "
                if b.total_prestamos and b.total_prestamos > 0:
                    speak += f"Ha sido prestado {b.total_prestamos} veces. "
                speak += _choose(ALGO_MAS)
                return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
            else:
                listado = ", ".join([f"'{b.titulo}'" for b in encontrados[:3]])
                speak = f"Encontré {len(encontrados)} libros que coinciden con '{titulo}': {listado}. " + _choose(ALGO_MAS)
                return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en BuscarLibroHandler")
            return handler_input.response_builder.speak("Hubo un problema buscando el libro. ¿Intentamos de nuevo?").ask("¿Qué libro buscas?").response
