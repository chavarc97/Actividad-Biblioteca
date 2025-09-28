
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

class ListarLibrosHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ListarLibrosIntent")(handler_input)

    def _filtrar(self, user_id: str, autor: Optional[str], filtro: Optional[str], service: BookService):
        if autor:
            return service.search_books_by_author(user_id, autor.strip())
        if filtro:
            f = filtro.lower()
            if f in ["prestados","prestado"]:
                return service.get_loaned_books(user_id)
            if f in ["disponibles","disponible"]:
                return service.get_available_books(user_id)
        return service.get_all_books(user_id)

    def handle(self, handler_input):
        try:
            sa = handler_input.attributes_manager.session_attributes
            user_id = _user_id(handler_input)
            autor = _slot(handler_input, "autor")
            filtro = _slot(handler_input, "filtro_tipo")

            # Si venimos de siguiente página, reutilizar filtros guardados
            if not autor and not filtro and sa.get("listando_libros"):
                autor = sa.get("autor")
                filtro = sa.get("filtro")

            service = self.factory.get_book_service(handler_input)
            libros = self._filtrar(user_id, autor, filtro, service) or []

            if not libros:
                return handler_input.response_builder.speak("No encontré libros con ese filtro. " + _choose(ALGO_MAS)).ask(_choose(PREGUNTAS_QUE_HACER)).response

            pagina = sa.get("pagina_libros", 0)
            inicio = pagina * LIBROS_POR_PAGINA
            fin = min(inicio + LIBROS_POR_PAGINA, len(libros))
            libros_pagina = libros[inicio:fin]

            if len(libros) <= LIBROS_POR_PAGINA:
                titulos = ", ".join([f"'{l.titulo}'" for l in libros])
                sa["pagina_libros"] = 0
                sa["listando_libros"] = False
                return handler_input.response_builder.speak(f"Tienes {len(libros)} libros: {titulos}. " + _choose(ALGO_MAS)).ask(_choose(PREGUNTAS_QUE_HACER)).response

            # hay paginación
            if pagina == 0:
                speak = f"Tienes {len(libros)} libros. Te los mostraré de {LIBROS_POR_PAGINA} en {LIBROS_POR_PAGINA}. "
            else:
                speak = f"Página {pagina+1}. "
            speak += f"Libros del {inicio+1} al {fin}: " + ", ".join([f"'{l.titulo}'" for l in libros_pagina]) + ". "

            if fin < len(libros):
                speak += f"Quedan {len(libros)-fin} libros más. Di 'siguiente' para continuar o 'salir' para terminar."
                sa["pagina_libros"] = pagina + 1
                sa["listando_libros"] = True
                sa["autor"] = autor
                sa["filtro"] = filtro
                ask = "¿Quieres ver más libros? Di 'siguiente' o 'salir'."
            else:
                sa["pagina_libros"] = 0
                sa["listando_libros"] = False
                ask = _choose(PREGUNTAS_QUE_HACER)
                speak += "Esos son todos los libros. " + _choose(ALGO_MAS)

            return handler_input.response_builder.speak(speak).ask(ask).response
        except Exception:
            logger.exception("Error en ListarLibrosHandler")
            handler_input.attributes_manager.session_attributes = {}
            return handler_input.response_builder.speak("Hubo un problema consultando tu biblioteca. ¿Intentamos de nuevo?").ask("¿Qué te gustaría hacer?").response
