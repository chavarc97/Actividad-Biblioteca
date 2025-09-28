import os
import logging

# SDK de Alexa
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.skill_builder import CustomSkillBuilder
from ask_sdk_s3.adapter import S3Adapter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

USE_FAKE_S3 = os.getenv("USE_FAKE_S3", "false").lower() == "true"

_FAKE_STORE = {}
class FakeS3Adapter:
    def __init__(self):
        logger.info("Usando FakeS3Adapter (memoria)")

    @staticmethod
    def _user_id_from_envelope(request_envelope):
        return request_envelope.context.system.user.user_id

    def get_attributes(self, request_envelope):
        uid = self._user_id_from_envelope(request_envelope)
        return _FAKE_STORE.get(uid, {})

    def save_attributes(self, request_envelope, attributes):
        uid = self._user_id_from_envelope(request_envelope)
        _FAKE_STORE[uid] = attributes or {}

    def delete_attributes(self, request_envelope):
        uid = self._user_id_from_envelope(request_envelope)
        _FAKE_STORE.pop(uid, None)

if USE_FAKE_S3:
    persistence_adapter = FakeS3Adapter()
else:
    bucket = os.environ.get("S3_PERSISTENCE_BUCKET")
    if not bucket:
        raise RuntimeError("Falta S3_PERSISTENCE_BUCKET (o usa USE_FAKE_S3=true)")
    persistence_adapter = S3Adapter(bucket_name=bucket)


# Imports de handlers (carpeta handlers/)

from handlers.launch_handler import LaunchRequestHandler
from handlers.mostrar_opciones_handler import MostrarOpcionesHandler
from handlers.continuar_agregar_handler import ContinuarAgregarHandler
from handlers.agregar_handler import AgregarLibroHandler
from handlers.eliminar_handler import EliminarLibroHandler
from handlers.listar_handler import ListarLibrosHandler
from handlers.buscar_handler import BuscarLibroHandler
from handlers.prestar_handler import PrestarLibroHandler
from handlers.devolver_handler import DevolverLibroHandler
from handlers.consultar_prestamos_handler import ConsultarPrestamosHandler
from handlers.consultar_devueltos_handler import ConsultarDevueltosHandler
from handlers.limpiar_cache_handler import LimpiarCacheHandler
from handlers.siguiente_pagina_handler import SiguientePaginaHandler
from handlers.salir_listado_handler import SalirListadoHandler
from handlers.ayuda_handler import AyudaHandler              
from handlers.cancel_stop_handler import CancelStopHandler   
from handlers.fallback_handler import FallbackHandler        
from handlers.session_ended_handler import SessionEndedHandler


# SkillBuilder y registro

sb = CustomSkillBuilder(persistence_adapter=persistence_adapter)

# Bienvenida
sb.add_request_handler(LaunchRequestHandler())

# Flujo de agregar (primero “continuar”, luego “agregar”)
sb.add_request_handler(ContinuarAgregarHandler())
sb.add_request_handler(AgregarLibroHandler())

# Opciones / listado / búsqueda
sb.add_request_handler(MostrarOpcionesHandler())
sb.add_request_handler(ListarLibrosHandler())
sb.add_request_handler(BuscarLibroHandler())

# Préstamos / devoluciones / consultas
sb.add_request_handler(PrestarLibroHandler())
sb.add_request_handler(DevolverLibroHandler())
sb.add_request_handler(ConsultarPrestamosHandler())
sb.add_request_handler(ConsultarDevueltosHandler())

sb.add_request_handler(LimpiarCacheHandler())
sb.add_request_handler(SiguientePaginaHandler())
sb.add_request_handler(SalirListadoHandler())

# Intents estándar
sb.add_request_handler(AyudaHandler())
sb.add_request_handler(CancelStopHandler())
sb.add_request_handler(FallbackHandler())
sb.add_request_handler(SessionEndedHandler())


handler = sb.lambda_handler()
