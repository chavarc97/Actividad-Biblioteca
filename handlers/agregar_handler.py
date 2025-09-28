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

from interfaces.repository_interface import IBookRepository, ILoanRepository  # solo para type hints
from services.book_service import BookService

class AgregarLibroHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("AgregarLibroIntent")(handler_input)

    def handle(self, handler_input):
        try:
            sa = handler_input.attributes_manager.session_attributes
            titulo = _slot(handler_input, "titulo") or sa.get("titulo_temp")
            autor = _slot(handler_input, "autor") or sa.get("autor_temp")
            tipo = _slot(handler_input, "tipo") or sa.get("tipo_temp")

            if not titulo:
                sa.update({"agregando_libro": True, "esperando": "titulo"})
                return handler_input.response_builder.speak("¡Perfecto! Vamos a agregar un libro. ¿Cuál es el título?").ask("¿Cuál es el título del libro?").response

            sa["titulo_temp"] = titulo
            if not autor:
                sa.update({"agregando_libro": True, "esperando": "autor"})
                return handler_input.response_builder.speak(f"¡'{titulo}' suena interesante! ¿Quién es el autor? Si no lo sabes, di: no sé.").ask("¿Quién es el autor?").response

            sa["autor_temp"] = autor
            if not tipo:
                sa.update({"agregando_libro": True, "esperando": "tipo"})
                autor_text = f" de {autor}" if autor and autor.lower() not in ["no sé", "no se", "no lo sé"] else ""
                return handler_input.response_builder.speak(f"Casi listo con '{titulo}'{autor_text}. ¿De qué tipo o género es? Si no sabes, di: no sé.").ask("¿De qué tipo es el libro?").response

            # normalizaciones
            if autor and autor.lower() in ["no sé","no se","no lo sé"]:
                autor = "Desconocido"
            if tipo and tipo.lower() in ["no sé","no se","no lo sé"]:
                tipo = "Sin categoría"

            service = self.factory.get_book_service(handler_input)
            ok, msg, book = service.add_book(_user_id(handler_input), titulo, autor, tipo)

            # limpiar sesión
            handler_input.attributes_manager.session_attributes = {}
            speak = msg if msg else f"¡Perfecto! He agregado '{titulo}'. "
            speak += " " + _choose(ALGO_MAS)
            return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en AgregarLibroHandler")
            handler_input.attributes_manager.session_attributes = {}
            return handler_input.response_builder.speak("Hubo un problema agregando el libro. Intentemos de nuevo.").ask("¿Qué libro quieres agregar?").response
