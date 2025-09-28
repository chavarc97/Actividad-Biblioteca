
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
from datetime import datetime

class ConsultarPrestamosHandler(AbstractRequestHandler):
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        return ask_utils.is_intent_name("ConsultarPrestamosIntent")(handler_input)

    def handle(self, handler_input):
        try:
            service = self.factory.get_loan_service(handler_input)
            loans = service.get_active_loans(_user_id(handler_input)) or []
            if not loans:
                speak = "¡Excelente! No tienes ningún libro prestado en este momento. " + _choose(ALGO_MAS)
                return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response

            if len(loans) == 1:
                speak = "Déjame ver... Solo tienes un libro prestado: "
            else:
                speak = f"Déjame revisar... Tienes {len(loans)} libros prestados: "

            detalles = []
            hay_vencidos = False
            hay_proximos = False
            now = datetime.now()
            for l in loans[:5]:
                dias = (l.fecha_limite - now).days
                texto = f"'{l.titulo}' está con {l.persona}"
                if dias < 0:
                    texto += " (¡ya venció!)"
                    hay_vencidos = True
                elif dias == 0:
                    texto += " (vence hoy)"
                    hay_proximos = True
                elif dias <= 2:
                    texto += f" (vence en {dias} días)"
                    hay_proximos = True
                detalles.append(texto)

            speak += "; ".join(detalles) + ". "
            if len(loans) > 5:
                speak += f"Y {len(loans)-5} más. "
            if hay_vencidos:
                speak += "Te sugiero pedir la devolución de los libros vencidos. "
            elif hay_proximos:
                speak += "Algunos están por vencer, ¡no lo olvides! "
            speak += _choose(ALGO_MAS)
            return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception:
            logger.exception("Error en ConsultarPrestamosHandler")
            return handler_input.response_builder.speak("Hubo un problema consultando los préstamos. ¿Intentamos de nuevo?").ask("¿Qué más deseas hacer?").response
