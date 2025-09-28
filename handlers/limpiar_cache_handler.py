
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

class LimpiarCacheHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("LimpiarCacheIntent")(handler_input)

    def handle(self, handler_input):
        try:
            user_id = _user_id(handler_input)

            cache = self.factory.get_cache_service()
            if cache:
                cache.delete(f"user_data_{user_id}")

            # Limpiar sesión
            handler_input.attributes_manager.session_attributes = {}

            # Releer y sincronizar desde persistencia
            user_data = DatabaseManager.get_user_data(handler_input)
            # nada más, BookService sincroniza estados cuando consulta

            total_libros = len(user_data.get("libros_disponibles", []))
            prestamos = len(user_data.get("prestamos_activos", []))
            speak = f"He limpiado el cache. Tienes {total_libros} libros en total y {prestamos} préstamos activos. " + _choose(ALGO_MAS)
            return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en LimpiarCacheHandler")
            return handler_input.response_builder.speak("Hubo un problema limpiando el cache. Intenta de nuevo.").ask("¿Qué deseas hacer?").response
