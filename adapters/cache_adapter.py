"""
Servicio de cache en memoria
Implementa ICacheService aplicando principios SOLID
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from interfaces.repository_interface import ICacheService


logger = logging.getLogger(__name__)


class MemoryCacheService(ICacheService):
    """
    Implementación de cache en memoria con TTL
    
    Principios aplicados:
    - Single Responsibility: Solo manejo de cache
    - Interface Segregation: Implementa solo métodos de cache necesarios
    """
    
    def __init__(self):
        """Constructor del servicio de cache"""
        self._cache: Dict[str, Dict[str, Any]] = {}
        logger.info("MemoryCacheService initialized")
    
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos del cache
        
        Args:
            key: Clave del cache
        
        Returns:
            Datos del cache o None si no existe o expiró
        """
        if key not in self._cache:
            return None
        
        item = self._cache[key]
        expire_at = item.get("expire_at")
        
        # Verificar si expiró
        if expire_at and datetime.now().timestamp() > expire_at:
            del self._cache[key]
            logger.info(f"Cache item expired and removed: {key}")
            return None
        
        logger.info(f"Cache hit: {key}")
        return item.get("data")
    
    def set(self, key: str, data: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        """
        Guarda datos en cache con TTL
        
        Args:
            key: Clave del cache
            data: Datos a guardar
            ttl_seconds: Tiempo de vida en segundos (default 1 hora)
        """
        expire_at = (datetime.now() + timedelta(seconds=ttl_seconds)).timestamp()
        
        self._cache[key] = {
            "data": data.copy() if isinstance(data, dict) else data,
            "expire_at": expire_at,
            "created_at": datetime.now().timestamp()
        }
        
        logger.info(f"Cache item saved: {key} (TTL: {ttl_seconds}s)")
    
    def delete(self, key: str) -> None:
        """
        Elimina datos del cache
        
        Args:
            key: Clave del cache
        """
        if key in self._cache:
            del self._cache[key]
            logger.info(f"Cache item deleted: {key}")
    
    def clear_all(self) -> None:
        """
        Limpia todo el cache
        """
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared - {cache_size} items removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del cache
        
        Returns:
            Diccionario con estadísticas
        """
        now = datetime.now().timestamp()
        active_items = 0
        expired_items = 0
        
        for item in self._cache.values():
            expire_at = item.get("expire_at")
            if expire_at and now > expire_at:
                expired_items += 1
            else:
                active_items += 1
        
        return {
            "total_items": len(self._cache),
            "active_items": active_items,
            "expired_items": expired_items,
            "memory_usage_estimate": self._estimate_memory_usage()
        }
    
    def cleanup_expired(self) -> int:
        """
        Limpia elementos expirados del cache
        
        Returns:
            Número de elementos eliminados
        """
        now = datetime.now().timestamp()
        expired_keys = []
        
        for key, item in self._cache.items():
            expire_at = item.get("expire_at")
            if expire_at and now > expire_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache items")
        
        return len(expired_keys)
    
    def _estimate_memory_usage(self) -> str:
        """
        Estima el uso de memoria del cache
        
        Returns:
            Estimación del uso de memoria como string
        """
        try:
            import sys
            total_size = sys.getsizeof(self._cache)
            
            for item in self._cache.values():
                total_size += sys.getsizeof(item)
                total_size += sys.getsizeof(item.get("data", {}))
            
            # Convertir a KB/MB
            if total_size < 1024:
                return f"{total_size} bytes"
            elif total_size < 1024 * 1024:
                return f"{total_size / 1024:.1f} KB"
            else:
                return f"{total_size / (1024 * 1024):.1f} MB"
                
        except Exception:
            return "Unknown"