
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

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        try:
            # limpiar estado de sesión
            handler_input.attributes_manager.session_attributes = {}
            factory = get_service_factory()
            # Asegurar datos de usuario existen
            user_data = DatabaseManager.get_user_data(handler_input)

            total_libros = len(user_data.get("libros_disponibles", []))
            prestamos_activos = len(user_data.get("prestamos_activos", []))

            # usuario frecuente simple
            historial = user_data.get("historial_conversaciones", [])
            es_frecuente = len(historial) > 5
            saludo = "¡Hola!" if not SALUDOS else _choose(SALUDOS)
            if es_frecuente and total_libros > 0:
                saludo = "¡Hola de nuevo! ¡Qué bueno verte por aquí!"
                estado = f" Tienes {total_libros} libros" + (f" y {prestamos_activos} préstamos activos." if prestamos_activos else ".")
            else:
                estado = f" Tienes {total_libros} libros en tu colección." if total_libros>0 else " Empecemos a construir tu biblioteca."

            opciones = " " + (_choose(OPCIONES_MENU) if OPCIONES_MENU else "")
            pregunta = " " + (_choose(PREGUNTAS_QUE_HACER) if PREGUNTAS_QUE_HACER else "¿Qué te gustaría hacer?")
            speak_output = f"{saludo}{estado}{opciones}{pregunta}"

            # guardar entrada a historial de conversación
            user_data.setdefault("historial_conversaciones", []).append({
                "tipo": "inicio_sesion",
                "timestamp": IdGenerator.now_iso(),
                "accion": "bienvenida"
            })
            DatabaseManager.save_user_data(handler_input, user_data)

            return handler_input.response_builder.speak(speak_output).ask(_choose(PREGUNTAS_QUE_HACER)).response
        except Exception as e:
            logger.exception("Error en LaunchRequestHandler")
            return handler_input.response_builder.speak("¡Hola! Bienvenido a tu biblioteca. ¿En qué puedo ayudarte?").ask("¿Qué deseas hacer?").response
