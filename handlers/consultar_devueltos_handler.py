
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
from models.loan import LoanStatus

class ConsultarDevueltosHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ConsultarDevueltosIntent")(handler_input)

    def handle(self, handler_input):
        try:
            service = self.factory.get_loan_service(handler_input)
            historial = service.get_loan_history(_user_id(handler_input)) or []
            devueltos = [l for l in historial if l.estado == LoanStatus.DEVUELTO]
            if not devueltos:
                speak = "Aún no has registrado devoluciones. Cuando prestes libros y te los devuelvan, aparecerán aquí. "
            else:
                total = len(devueltos)
                speak = f"Has registrado {total} " + ("devolución en total. " if total==1 else "devoluciones en total. ")
                if total <= 10:
                    detalles = []
                    for h in devueltos:
                        d = f"'{h.titulo}'"
                        if h.persona and h.persona not in ['Alguien','un amigo']:
                            d += f" que prestaste a {h.persona}"
                        detalles.append(d)
                    speak += "Los libros devueltos son: " + ", ".join(detalles) + ". "
                else:
                    recientes = devueltos[-5:]
                    detalles = []
                    for h in reversed(recientes):
                        d = f"'{h.titulo}'"
                        if h.persona and h.persona not in ['Alguien','un amigo']:
                            d += f" a {h.persona}"
                        detalles.append(d)
                    speak += "Los 5 más recientes son: " + ", ".join(detalles) + ". "
            speak += _choose(ALGO_MAS)
            return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en ConsultarDevueltosHandler")
            return handler_input.response_builder.speak("Hubo un problema consultando el historial.").ask("¿Qué más deseas hacer?").response
