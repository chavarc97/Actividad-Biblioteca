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

LIBROS_POR_PAGINA = 10

class SiguientePaginaHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("SiguientePaginaIntent")(handler_input)

    def handle(self, handler_input):
        try:
            sa = handler_input.attributes_manager.session_attributes
            if not sa.get("listando_libros"):
                return handler_input.response_builder.speak("No estás en un listado, pero puedo listar tus libros. ¿Quieres que los muestre?").ask("¿Quieres que muestre tus libros?").response

            # reutiliza filtros guardados
            pagina = sa.get("pagina_libros", 0)
            autor = sa.get("autor")
            filtro = sa.get("filtro")
            user_id = _user_id(handler_input)
            service = self.factory.get_book_service(handler_input)

            # Obtener lista completa con mismo filtro
            if autor:
                libros = service.search_books_by_author(user_id, autor)
            elif filtro and filtro.lower() in ["prestados","prestado"]:
                libros = service.get_loaned_books(user_id)
            elif filtro and filtro.lower() in ["disponibles","disponible"]:
                libros = service.get_available_books(user_id)
            else:
                libros = service.get_all_books(user_id)
            libros = libros or []

            inicio = pagina * LIBROS_POR_PAGINA
            fin = min(inicio + LIBROS_POR_PAGINA, len(libros))
            libros_pagina = libros[inicio:fin]
            if not libros_pagina:
                sa["pagina_libros"] = 0
                sa["listando_libros"] = False
                return handler_input.response_builder.speak("Ya no hay más libros para mostrar. " + _choose(ALGO_MAS)).ask(_choose(PREGUNTAS_QUE_HACER)).response

            speak = f"Libros del {inicio+1} al {fin}: " + ", ".join([f"'{l.titulo}'" for l in libros_pagina]) + ". "
            if fin < len(libros):
                speak += f"Quedan {len(libros)-fin} libros más. Di 'siguiente' para continuar o 'salir' para terminar."
                sa["pagina_libros"] = pagina + 1
                sa["listando_libros"] = True
                ask = "¿Quieres que muestre más?"
            else:
                sa["pagina_libros"] = 0
                sa["listando_libros"] = False
                speak += "Esos son todos. " + _choose(ALGO_MAS)
                ask = _choose(PREGUNTAS_QUE_HACER)

            return handler_input.response_builder.speak(speak).ask(ask).response
        except Exception:
            logger.exception("Error en SiguientePaginaHandler")
            return handler_input.response_builder.speak("No pude avanzar de página. ¿Qué más te gustaría hacer?").ask(_choose(PREGUNTAS_QUE_HACER)).response
