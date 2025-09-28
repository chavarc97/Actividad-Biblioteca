"""
Factory para crear servicios aplicando principios SOLID
Implementa Factory Pattern y Dependency Injection
"""
import os
import logging
from typing import Optional, Dict, Any

# Importaciones de servicios
from services.book_service import BookService
from services.loan_service import LoanService

# Importaciones de repositorios
from repositories.book_repository import BookRepository
from repositories.loan_repository import LoanRepository

# Importaciones de adaptadores
from adapters.s3_adapter import S3DataAdapter, FakeS3DataAdapter
from adapters.cache_adapter import MemoryCacheService

# Importaciones de interfaces
from interfaces.repository_interface import IDataAdapter, ICacheService

logger = logging.getLogger(__name__)


class ServiceFactory:
    """
    Factory para crear servicios con sus dependencias
    
    Principios aplicados:
    - Single Responsibility: Solo creación de servicios
    - Dependency Inversion: Inyecta dependencias apropiadas
    - Factory Pattern: Encapsula la creación de objetos complejos
    - Singleton Pattern: Una instancia por tipo de servicio
    """
    
    def __init__(self):
        """Constructor de la factory"""
        # Instancias singleton de componentes base
        self._data_adapter: Optional[IDataAdapter] = None
        self._cache_service: Optional[ICacheService] = None
        self._book_repository: Optional[BookRepository] = None
        self._loan_repository: Optional[LoanRepository] = None
        
        # Configuración desde variables de entorno
        self._use_fake_s3 = os.getenv("USE_FAKE_S3", "false").lower() == "true"
        self._enable_cache = os.getenv("ENABLE_CACHE", "true").lower() == "true"
        self._s3_bucket = os.environ.get("S3_PERSISTENCE_BUCKET")
        
        logger.info(f"ServiceFactory initialized - Fake S3: {self._use_fake_s3}, Cache: {self._enable_cache}")
    
    def get_data_adapter(self) -> IDataAdapter:
        """
        Obtiene o crea el adaptador de datos (Singleton)
        
        Returns:
            Instancia del adaptador de datos
        """
        if self._data_adapter is None:
            if self._use_fake_s3:
                self._data_adapter = FakeS3DataAdapter()
                logger.info("Created FakeS3DataAdapter")
            else:
                if not self._s3_bucket:
                    raise RuntimeError("S3_PERSISTENCE_BUCKET es requerido cuando USE_FAKE_S3=false")
                
                self._data_adapter = S3DataAdapter(self._s3_bucket)
                logger.info(f"Created S3DataAdapter with bucket: {self._s3_bucket}")
        
        return self._data_adapter
    
    def get_cache_service(self) -> Optional[ICacheService]:
        """
        Obtiene o crea el servicio de cache (Singleton)
        
        Returns:
            Instancia del servicio de cache o None si está deshabilitado
        """
        if not self._enable_cache:
            return None
        
        if self._cache_service is None:
            self._cache_service = MemoryCacheService()
            logger.info("Created MemoryCacheService")
        
        return self._cache_service
    
    def get_book_repository(self, handler_input=None) -> BookRepository:
        """
        Obtiene o crea el repositorio de libros (Singleton)
        
        Args:
            handler_input: Input del handler (para futuras extensiones)
        
        Returns:
            Instancia del repositorio de libros
        """
        if self._book_repository is None:
            data_adapter = self.get_data_adapter()
            cache_service = self.get_cache_service()
            
            self._book_repository = BookRepository(data_adapter, cache_service)
            logger.info("Created BookRepository")
        
        return self._book_repository
    
    def get_loan_repository(self, handler_input=None) -> LoanRepository:
        """
        Obtiene o crea el repositorio de préstamos (Singleton)
        
        Args:
            handler_input: Input del handler (para futuras extensiones)
        
        Returns:
            Instancia del repositorio de préstamos
        """
        if self._loan_repository is None:
            data_adapter = self.get_data_adapter()
            cache_service = self.get_cache_service()
            
            self._loan_repository = LoanRepository(data_adapter, cache_service)
            logger.info("Created LoanRepository")
        
        return self._loan_repository
    
    def get_book_service(self, handler_input=None) -> BookService:
        """
        Obtiene una NUEVA instancia del servicio de libros
        Los servicios son stateless, se crean nuevos cada vez
        
        Args:
            handler_input: Input del handler (para futuras extensiones)
        
        Returns:
            Nueva instancia del servicio de libros
        """
        book_repository = self.get_book_repository(handler_input)
        loan_repository = self.get_loan_repository(handler_input)
        
        return BookService(book_repository, loan_repository)
    
    def get_loan_service(self, handler_input=None) -> LoanService:
        """
        Obtiene una NUEVA instancia del servicio de préstamos
        Los servicios son stateless, se crean nuevos cada vez
        
        Args:
            handler_input: Input del handler (para futuras extensiones)
        
        Returns:
            Nueva instancia del servicio de préstamos
        """
        book_repository = self.get_book_repository(handler_input)
        loan_repository = self.get_loan_repository(handler_input)
        
        return LoanService(book_repository, loan_repository)
    
    def get_database_manager(self, handler_input) -> 'DatabaseManager':
        """
        Obtiene el database manager con datos reales del usuario
        Mantiene compatibilidad con código original
        
        Args:
            handler_input: Input del handler de Alexa
        
        Returns:
            Instancia de DatabaseManager configurada
        """
        return DatabaseManager(handler_input, self.get_data_adapter())
    
    def reset_cache(self) -> None:
        """
        Limpia el cache y reinicia los servicios
        Útil para testing y desarrollo
        """
        if self._cache_service:
            self._cache_service.clear_all()
            logger.info("Cache cleared")
        
        # Resetear instancias para forzar recreación
        self._book_repository = None
        self._loan_repository = None
        
        logger.info("ServiceFactory repositories reset")
    
    def reset_all(self) -> None:
        """
        Resetea TODOS los componentes de la factory
        Para testing exhaustivo
        """
        self.reset_cache()
        
        # Resetear TODOS los componentes
        self._data_adapter = None
        self._cache_service = None
        self._book_repository = None
        self._loan_repository = None
        
        logger.info("ServiceFactory completely reset")
    
    def configure_for_testing(self, use_fake_s3: bool = True, enable_cache: bool = False) -> None:
        """
        Configura la factory para testing
        
        Args:
            use_fake_s3: Si usar adaptador fake en lugar de S3 real
            enable_cache: Si habilitar cache (generalmente False para tests)
        """
        self._use_fake_s3 = use_fake_s3
        self._enable_cache = enable_cache
        
        # Resetear TODO para que use nueva configuración
        self.reset_all()
        
        logger.info(f"ServiceFactory configured for testing - Fake S3: {use_fake_s3}, Cache: {enable_cache}")
    
    def configure_for_production(self, s3_bucket: str, enable_cache: bool = True) -> None:
        """
        Configura la factory para producción
        
        Args:
            s3_bucket: Nombre del bucket S3
            enable_cache: Si habilitar cache (generalmente True)
        """
        self._use_fake_s3 = False
        self._enable_cache = enable_cache
        self._s3_bucket = s3_bucket
        
        # Resetear para aplicar configuración
        self.reset_all()
        
        logger.info(f"ServiceFactory configured for production - S3 bucket: {s3_bucket}, Cache: {enable_cache}")
    
    def get_factory_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la factory
        Útil para debugging y monitoreo
        
        Returns:
            Diccionario con estadísticas
        """
        stats = {
            "config": {
                "use_fake_s3": self._use_fake_s3,
                "enable_cache": self._enable_cache,
                "s3_bucket": self._s3_bucket or "Not configured"
            },
            "instances": {
                "data_adapter_created": self._data_adapter is not None,
                "cache_service_created": self._cache_service is not None,
                "book_repository_created": self._book_repository is not None,
                "loan_repository_created": self._loan_repository is not None
            }
        }
        
        # Agregar estadísticas de cache si existe
        if self._cache_service:
            stats["cache_stats"] = self._cache_service.get_stats()
        
        return stats


class DatabaseManager:
    """
    Manager para mantener compatibilidad con código original
    Actúa como bridge/adapter entre el código viejo y la nueva arquitectura
    """
    
    def __init__(self, handler_input, data_adapter: IDataAdapter):
        """
        Constructor
        
        Args:
            handler_input: Input del handler de Alexa
            data_adapter: Adaptador de datos inyectado
        """
        self.handler_input = handler_input
        self.data_adapter = data_adapter
        self.user_id = handler_input.request_envelope.context.system.user.user_id
        logger.info(f"DatabaseManager created for user: {self.user_id}")
    
    def get_user_data_instance(self) -> Dict[str, Any]:
        """
        Obtiene datos del usuario para esta instancia específica
        
        Returns:
            Datos del usuario
        """
        try:
            user_data = self.data_adapter.get_attributes(self.handler_input.request_envelope)
            
            if not user_data:
                user_data = self.initial_data()
                logger.info(f"Created initial data for user: {self.user_id}")
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error getting user data for {self.user_id}: {e}")
            return self.initial_data()
    
    def save_user_data_instance(self, data: Dict[str, Any]) -> None:
        """
        Guarda datos del usuario para esta instancia específica
        
        Args:
            data: Datos a guardar
        """
        try:
            self.data_adapter.save_attributes(self.handler_input.request_envelope, data)
            logger.info(f"Saved user data for {self.user_id}")
            
        except Exception as e:
            logger.error(f"Error saving user data for {self.user_id}: {e}")
            raise
    
    @staticmethod
    def get_user_data(handler_input) -> Dict[str, Any]:
        """
        Método estático para compatibilidad total con código original
        
        Args:
            handler_input: Input del handler
        
        Returns:
            Datos del usuario
        """
        factory = get_service_factory()
        data_adapter = factory.get_data_adapter()
        
        try:
            user_data = data_adapter.get_attributes(handler_input.request_envelope)
            
            if not user_data:
                user_data = DatabaseManager.initial_data()
                # Guardar estructura inicial
                data_adapter.save_attributes(handler_input.request_envelope, user_data)
                logger.info("Created and saved initial user data structure")
            
            return user_data
            
        except Exception as e:
            logger.error(f"Error in static get_user_data: {e}")
            return DatabaseManager.initial_data()
    
    @staticmethod
    def save_user_data(handler_input, data: Dict[str, Any]) -> None:
        """
        Método estático para compatibilidad total con código original
        
        Args:
            handler_input: Input del handler
            data: Datos a guardar
        """
        factory = get_service_factory()
        data_adapter = factory.get_data_adapter()
        cache_service = factory.get_cache_service()
        
        try:
            # Guardar en persistencia principal
            data_adapter.save_attributes(handler_input.request_envelope, data)
            
            # También actualizar cache si existe
            if cache_service:
                user_id = handler_input.request_envelope.context.system.user.user_id
                cache_key = f"user_data_{user_id}"
                cache_service.set(cache_key, data, ttl_seconds=3600)
                logger.info(f"Updated cache for user: {user_id}")
                
            logger.info("User data saved successfully")
                
        except Exception as e:
            logger.error(f"Error in static save_user_data: {e}")
            raise
    
    @staticmethod
    def initial_data() -> Dict[str, Any]:
        """
        Retorna estructura inicial de datos para un usuario nuevo
        
        Returns:
            Diccionario con estructura inicial completa
        """
        from datetime import datetime
        
        return {
            "libros_disponibles": [],
            "prestamos_activos": [],
            "historial_prestamos": [],
            "estadisticas": {
                "total_libros": 0,
                "total_prestamos": 0,
                "total_devoluciones": 0,
                "prestamos_activos": 0
            },
            "historial_conversaciones": [],
            "configuracion": {
                "limite_prestamos": 10,
                "dias_prestamo": 7
            },
            "usuario_frecuente": False,
            "fecha_creacion": datetime.now().isoformat(),
            "version": "2.0"
        }
    
    @staticmethod
    def _user_id(handler_input) -> str:
        """
        Extrae el user_id del handler input
        Método de utilidad para compatibilidad
        
        Args:
            handler_input: Input del handler
        
        Returns:
            User ID del usuario
        """
        return handler_input.request_envelope.context.system.user.user_id


# =================================================
# SINGLETON PATTERN PARA FACTORY GLOBAL
# =================================================

_service_factory_instance = None


def get_service_factory() -> ServiceFactory:
    """
    Obtiene la instancia global de ServiceFactory (Singleton Pattern)
    
    Returns:
        Instancia global de ServiceFactory
    """
    global _service_factory_instance
    if _service_factory_instance is None:
        _service_factory_instance = ServiceFactory()
        logger.info("Created global ServiceFactory instance")
    return _service_factory_instance


def reset_service_factory() -> None:
    """
    Resetea la instancia global de ServiceFactory
    Útil para testing y desarrollo
    """
    global _service_factory_instance
    if _service_factory_instance:
        _service_factory_instance.reset_all()
        logger.info("Reset global ServiceFactory instance")
    _service_factory_instance = None


def configure_service_factory_for_testing() -> ServiceFactory:
    """
    Configura y obtiene factory para testing
    Función de conveniencia para tests
    
    Returns:
        Factory configurada para testing
    """
    reset_service_factory()
    factory = get_service_factory()
    factory.configure_for_testing(use_fake_s3=True, enable_cache=False)
    return factory


def configure_service_factory_for_production(s3_bucket: str) -> ServiceFactory:
    """
    Configura y obtiene factory para producción
    Función de conveniencia para producción
    
    Args:
        s3_bucket: Nombre del bucket S3
    
    Returns:
        Factory configurada para producción
    """
    reset_service_factory()
    factory = get_service_factory()
    factory.configure_for_production(s3_bucket, enable_cache=True)
    return factory
