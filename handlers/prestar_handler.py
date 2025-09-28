
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

class PrestarLibroHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("PrestarLibroIntent")(handler_input)

    def handle(self, handler_input):
        try:
            titulo = _slot(handler_input, "titulo")
            persona = _slot(handler_input, "nombre_persona")
            if not titulo:
                return handler_input.response_builder.speak("¿Qué libro quieres prestar?").ask("¿Cuál es el título del libro?").response

            service = self.factory.get_loan_service(handler_input)
            ok, msg, loan = service.create_loan(_user_id(handler_input), book_title=titulo, person_name=persona)
            if not ok:
                return handler_input.response_builder.speak(msg).ask("¿Quieres intentar con otro libro?").response

            fecha_limite = IdGenerator.format_date_es(loan.fecha_limite)
            persona_text = f" a {loan.persona}" if loan.persona else ""
            speak = f"{_choose(CONFIRMACIONES)} He registrado el préstamo de '{loan.titulo}'{persona_text}. La fecha de devolución es el {fecha_limite}. "
            speak += _choose(ALGO_MAS)
            return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en PrestarLibroHandler")
            return handler_input.response_builder.speak("Ups, tuve un problema registrando el préstamo. ¿Lo intentamos de nuevo?").ask("¿Qué libro quieres prestar?").response
