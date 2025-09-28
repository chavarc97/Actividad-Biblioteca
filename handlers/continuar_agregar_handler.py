
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

class ContinuarAgregarHandler(AbstractRequestHandler):
    """
    Continúa el flujo de agregar libro cuando estamos esperando título/autor/tipo.
    Se activa si hay estado de sesión 'agregando_libro' y no es otro intent de control.
    """
    def __init__(self):
        self.factory = get_service_factory()

    def can_handle(self, handler_input):
        sa = handler_input.attributes_manager.session_attributes
        return bool(sa.get("agregando_libro")) and not ask_utils.is_intent_name("AgregarLibroIntent")(handler_input) and not ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) and not ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)

    def _extract_free_text(self, handler_input) -> Optional[str]:
        # intento 1: RespuestaGeneralIntent.respuesta
        if ask_utils.is_intent_name("RespuestaGeneralIntent")(handler_input):
            val = _slot(handler_input, "respuesta")
            if val: 
                return val
        # intento 2: primer slot con valor
        try:
            intent = handler_input.request_envelope.request.intent
            if intent and intent.slots:
                for s in intent.slots.values():
                    if getattr(s, "value", None):
                        return s.value
        except Exception:
            pass
        return None

    def handle(self, handler_input):
        try:
            sa = handler_input.attributes_manager.session_attributes
            esperando = sa.get("esperando")
            valor = self._extract_free_text(handler_input)
            logger.info(f"ContinuarAgregar: esperando={esperando}, valor={valor}")

            if esperando == "titulo":
                if valor:
                    sa["titulo_temp"] = valor
                    sa["esperando"] = "autor"
                    return handler_input.response_builder.speak(f"¡'{valor}' suena interesante! ¿Quién es el autor? Si no lo sabes, di: no sé el autor.").ask("¿Quién es el autor?").response
                else:
                    return handler_input.response_builder.speak("No entendí el título. Di: 'el título es' seguido del nombre.").ask("¿Cuál es el título del libro?").response

            if esperando == "autor":
                if not valor or valor.lower() in ["no sé","no se","no lo sé","no lo se","no sé el autor","no se el autor"]:
                    valor = "Desconocido"
                elif valor.lower().startswith("el autor es "):
                    valor = valor[12:].strip()
                elif valor.lower().startswith("es "):
                    valor = valor[3:].strip()

                sa["autor_temp"] = valor
                sa["esperando"] = "tipo"
                titulo = sa.get("titulo_temp")
                autor_text = f" de {valor}" if valor != "Desconocido" else ""
                return handler_input.response_builder.speak(f"Perfecto, '{titulo}'{autor_text}. ¿De qué tipo o género es? Si no sabes, di: no sé el tipo.").ask("¿De qué tipo es el libro?").response

            if esperando == "tipo":
                if not valor or valor.lower() in ["no sé","no se","no lo sé","no lo se","no sé el tipo","no se el tipo"]:
                    valor = "Sin categoría"
                elif valor.lower().startswith("el tipo es "):
                    valor = valor[11:].strip()
                elif valor.lower().startswith("es "):
                    valor = valor[3:].strip()

                titulo = sa.get("titulo_temp")
                autor = sa.get("autor_temp","Desconocido")
                tipo = valor

                service = self.factory.get_book_service(handler_input)
                ok, msg, book = service.add_book(_user_id(handler_input), titulo, autor, tipo)
                handler_input.attributes_manager.session_attributes = {}
                speak = msg if msg else f"¡Perfecto! He agregado '{titulo}'. "
                speak += " " + _choose(ALGO_MAS)
                return handler_input.response_builder.speak(speak).ask(_choose(PREGUNTAS_QUE_HACER)).response

            # fallback
            handler_input.attributes_manager.session_attributes = {}
            return handler_input.response_builder.speak("Hubo un problema. Empecemos de nuevo. ¿Qué libro quieres agregar?").ask("¿Qué libro quieres agregar?").response
        except Exception:
            logger.exception("Error en ContinuarAgregarHandler")
            handler_input.attributes_manager.session_attributes = {}
            return handler_input.response_builder.speak("Hubo un problema. Intentemos agregar el libro de nuevo.").ask("¿Qué libro quieres agregar?").response
