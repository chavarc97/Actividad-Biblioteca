import logging
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_model import Response
import random
from helpers.utils import ResponsePhrases


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """
    Handler para los intents de cancelar y detener (AMAZON.CancelIntent y AMAZON.StopIntent)
    """
    def can_handle(self, handler_input):
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # Limpiar sesión al salir
        handler_input.attributes_manager.session_attributes = {}
        
        return (
            handler_input.response_builder
                .speak(ResponsePhrases.get_random_phrase(ResponsePhrases.DESPEDIDAS))
                .response
        )
        

class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # Limpiar sesión
        handler_input.attributes_manager.session_attributes = {}
        return handler_input.response_builder.response
