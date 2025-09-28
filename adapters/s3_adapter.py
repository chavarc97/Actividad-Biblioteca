"""
Adaptador S3 mejorado con principios SOLID
Implementa IDataAdapter para abstracción de persistencia
"""
import json
import logging
from typing import Dict, Any, Optional

from interfaces.repository_interface import IDataAdapter
from ask_sdk_s3.adapter import S3Adapter as AskS3Adapter


logger = logging.getLogger(__name__)


class S3DataAdapter(IDataAdapter):
    """
    Adaptador para persistencia en S3
    
    Principios aplicados:
    - Single Responsibility: Solo manejo de persistencia S3
    - Open/Closed: Abierto para extensión, cerrado para modificación
    - Dependency Inversion: Implementa interfaz abstracta
    """
    
    def __init__(self, bucket_name: str):
        """
        Constructor del adaptador S3
        
        Args:
            bucket_name: Nombre del bucket S3
        """
        self._bucket_name = bucket_name
        self._s3_adapter = AskS3Adapter(bucket_name=bucket_name)
        logger.info(f"S3DataAdapter initialized with bucket: {bucket_name}")
    
    def get_attributes(self, request_envelope) -> Dict[str, Any]:
        """
        Obtiene atributos persistentes del usuario desde S3
        
        Args:
            request_envelope: Envelope de la request de Alexa
        
        Returns:
            Diccionario con atributos del usuario
        """
        try:
            attributes = self._s3_adapter.get_attributes(request_envelope)
            
            # Si no hay atributos, retornar estructura inicial
            if not attributes:
                attributes = self._get_initial_user_data()
                logger.info("No existing attributes found, returning initial data structure")
            
            # Validar y normalizar estructura
            attributes = self._validate_and_normalize_data(attributes)
            
            return attributes
            
        except Exception as e:
            logger.error(f"Error getting attributes from S3: {e}")
            # Retornar estructura inicial en caso de error
            return self._get_initial_user_data()
    
    def save_attributes(self, request_envelope, attributes: Dict[str, Any]) -> None:
        """
        Guarda atributos persistentes del usuario en S3
        
        Args:
            request_envelope: Envelope de la request de Alexa
            attributes: Atributos a guardar
        """
        try:
            # Validar y normalizar datos antes de guardar
            normalized_attributes = self._validate_and_normalize_data(attributes)
            
            # Guardar en S3
            self._s3_adapter.save_attributes(request_envelope, normalized_attributes)
            logger.info("Attributes saved successfully to S3")
            
        except Exception as e:
            logger.error(f"Error saving attributes to S3: {e}")
            raise
    
    def delete_attributes(self, request_envelope) -> None:
        """
        Elimina todos los atributos del usuario de S3
        
        Args:
            request_envelope: Envelope de la request de Alexa
        """
        try:
            self._s3_adapter.delete_attributes(request_envelope)
            logger.info("Attributes deleted successfully from S3")
            
        except Exception as e:
            logger.error(f"Error deleting attributes from S3: {e}")
            raise
    
    def _get_initial_user_data(self) -> Dict[str, Any]:
        """
        Obtiene la estructura inicial de datos para un usuario nuevo
        
        Returns:
            Diccionario con estructura inicial
        """
        return {
            "libros_disponibles": [],
            "prestamos_activos": [],
            "historial_prestamos": [],
            "estadisticas": {
                "total_libros": 0,
                "total_prestamos": 0,
                "total_devoluciones": 0
            },
            "historial_conversaciones": [],
            "configuracion": {
                "limite_prestamos": 10,
                "dias_prestamo": 7
            },
            "usuario_frecuente": False,
            "version": "2.0"  # Para futuras migraciones
        }
    
    def _validate_and_normalize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida y normaliza la estructura de datos
        
        Args:
            data: Datos a validar
        
        Returns:
            Datos validados y normalizados
        """
        if not isinstance(data, dict):
            logger.warning("Data is not a dictionary, returning initial structure")
            return self._get_initial_user_data()
        
        # Asegurar que existan las claves principales
        initial_data = self._get_initial_user_data()
        
        for key, default_value in initial_data.items():
            if key not in data:
                data[key] = default_value
                logger.info(f"Added missing key '{key}' with default value")
        
        # Validar tipos específicos
        self._validate_books_data(data)
        self._validate_loans_data(data)
        self._validate_statistics_data(data)
        
        return data
    
    def _validate_books_data(self, data: Dict[str, Any]) -> None:
        """
        Valida la estructura de datos de libros
        
        Args:
            data: Datos a validar (se modifica in-place)
        """
        books = data.get("libros_disponibles", [])
        if not isinstance(books, list):
            logger.warning("libros_disponibles is not a list, resetting to empty list")
            data["libros_disponibles"] = []
            return
        
        # Validar cada libro
        valid_books = []
        for book_data in books:
            if isinstance(book_data, dict) and book_data.get("titulo"):
                # Asegurar que tenga ID
                if not book_data.get("id"):
                    book_data["id"] = self._generate_id()
                
                # Normalizar campos obligatorios
                book_data["titulo"] = str(book_data.get("titulo", "")).strip()
                book_data["autor"] = str(book_data.get("autor", "Desconocido")).strip()
                book_data["tipo"] = str(book_data.get("tipo", "Sin categoría")).strip()
                book_data["estado"] = book_data.get("estado", "disponible")
                book_data["total_prestamos"] = int(book_data.get("total_prestamos", 0))
                
                valid_books.append(book_data)
            else:
                logger.warning(f"Invalid book data found and removed: {book_data}")
        
        data["libros_disponibles"] = valid_books
    
    def _validate_loans_data(self, data: Dict[str, Any]) -> None:
        """
        Valida la estructura de datos de préstamos
        
        Args:
            data: Datos a validar (se modifica in-place)
        """
        # Validar préstamos activos
        active_loans = data.get("prestamos_activos", [])
        if not isinstance(active_loans, list):
            logger.warning("prestamos_activos is not a list, resetting to empty list")
            data["prestamos_activos"] = []
        else:
            valid_loans = []
            for loan_data in active_loans:
                if isinstance(loan_data, dict) and loan_data.get("libro_id"):
                    # Asegurar que tenga ID
                    if not loan_data.get("id"):
                        loan_data["id"] = self._generate_loan_id()
                    
                    valid_loans.append(loan_data)
                else:
                    logger.warning(f"Invalid active loan data found and removed: {loan_data}")
            data["prestamos_activos"] = valid_loans
        
        # Validar historial de préstamos
        loan_history = data.get("historial_prestamos", [])
        if not isinstance(loan_history, list):
            logger.warning("historial_prestamos is not a list, resetting to empty list")
            data["historial_prestamos"] = []
    
    def _validate_statistics_data(self, data: Dict[str, Any]) -> None:
        """
        Valida y actualiza estadísticas
        
        Args:
            data: Datos a validar (se modifica in-place)
        """
        stats = data.get("estadisticas", {})
        if not isinstance(stats, dict):
            stats = {}
        
        # Calcular estadísticas actuales
        books_count = len(data.get("libros_disponibles", []))
        active_loans_count = len(data.get("prestamos_activos", []))
        loan_history_count = len(data.get("historial_prestamos", []))
        
        # Actualizar estadísticas
        stats["total_libros"] = books_count
        stats["total_prestamos"] = stats.get("total_prestamos", 0)
        stats["total_devoluciones"] = stats.get("total_devoluciones", 0)
        stats["prestamos_activos"] = active_loans_count
        
        data["estadisticas"] = stats
    
    def _generate_id(self) -> str:
        """
        Genera un ID único para elementos
        
        Returns:
            ID único
        """
        import uuid
        return str(uuid.uuid4())[:8]
    
    def _generate_loan_id(self) -> str:
        """
        Genera un ID único para préstamos
        
        Returns:
            ID único para préstamo
        """
        from datetime import datetime
        return f"PREST-{datetime.now().strftime('%Y%m%d')}-{self._generate_id()}"


class FakeS3DataAdapter(IDataAdapter):
    """
    Adaptador falso para testing y desarrollo
    
    Simula el comportamiento de S3 en memoria
    """
    
    def __init__(self):
        """Constructor del adaptador fake"""
        self._store = {}
        logger.info("FakeS3DataAdapter initialized (memory-based)")
    
    def get_attributes(self, request_envelope) -> Dict[str, Any]:
        """
        Obtiene atributos del almacén en memoria
        
        Args:
            request_envelope: Envelope de la request de Alexa
        
        Returns:
            Diccionario con atributos del usuario
        """
        user_id = self._extract_user_id(request_envelope)
        attributes = self._store.get(user_id, {})
        
        if not attributes:
            # Retornar estructura inicial
            s3_adapter = S3DataAdapter("fake")
            attributes = s3_adapter._get_initial_user_data()
            self._store[user_id] = attributes
        
        return attributes
    
    def save_attributes(self, request_envelope, attributes: Dict[str, Any]) -> None:
        """
        Guarda atributos en el almacén en memoria
        
        Args:
            request_envelope: Envelope de la request de Alexa
            attributes: Atributos a guardar
        """
        user_id = self._extract_user_id(request_envelope)
        self._store[user_id] = attributes.copy()
        logger.info(f"FakeS3: Saved attributes for user {user_id}")
    
    def delete_attributes(self, request_envelope) -> None:
        """
        Elimina atributos del almacén en memoria
        
        Args:
            request_envelope: Envelope de la request de Alexa
        """
        user_id = self._extract_user_id(request_envelope)
        if user_id in self._store:
            del self._store[user_id]
            logger.info(f"FakeS3: Deleted attributes for user {user_id}")
    
    def _extract_user_id(self, request_envelope) -> str:
        """
        Extrae el user_id del request envelope
        
        Args:
            request_envelope: Envelope de la request
        
        Returns:
            User ID
        """
        return request_envelope.context.system.user.user_id