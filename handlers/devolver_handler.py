
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

from services.loan_service import LoanService

class DevolverLibroHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("DevolverLibroIntent")(handler_input)

    def handle(self, handler_input):
        try:
            titulo = _slot(handler_input, "titulo")
            id_prestamo = _slot(handler_input, "id_prestamo")
            if not titulo and not id_prestamo:
                return handler_input.response_builder.speak("¿Qué libro te devolvieron?").ask("Dime el título del libro.").response

            service = self.factory.get_loan_service(handler_input)
            ok, msg, loan = service.return_loan(_user_id(handler_input), book_title=titulo, loan_id=id_prestamo)
            if not ok:
                return handler_input.response_builder.speak(msg).ask("¿Cuál libro quieres devolver?").response

            a_tiempo = loan.fecha_devolucion and loan.fecha_limite and (loan.fecha_devolucion <= loan.fecha_limite)
            speak = f"{_choose(CONFIRMACIONES)} He registrado la devolución de '{loan.titulo}'. "
            speak += "¡Fue devuelto a tiempo! " if a_tiempo else "Fue devuelto un poco tarde, pero no hay problema. "
            speak += _choose(ALGO_MAS)
            return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en DevolverLibroHandler")
            return handler_input.response_builder.speak("Tuve un problema registrando la devolución. ¿Lo intentamos de nuevo?").ask("¿Qué libro quieres devolver?").response
