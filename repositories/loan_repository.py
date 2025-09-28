"""
Repositorio para manejo de datos de préstamos
Aplica el patrón Repository y principios SOLID
"""
from typing import List, Optional
import logging

from interfaces.repository_interface import ILoanRepository, IDataAdapter, ICacheService
from models.loan import Loan, LoanStatus
from datetime import datetime


logger = logging.getLogger(__name__)


class LoanRepository(ILoanRepository):
    """
    Implementación del repositorio de préstamos
    
    Principios aplicados:
    - Single Responsibility: Solo manejo de persistencia de préstamos
    - Dependency Inversion: Depende de abstracciones (IDataAdapter)
    """
    
    def __init__(self, data_adapter: IDataAdapter, cache_service: Optional[ICacheService] = None):
        """
        Constructor con inyección de dependencias
        
        Args:
            data_adapter: Adaptador de persistencia
            cache_service: Servicio de cache opcional
        """
        self._data_adapter = data_adapter
        self._cache_service = cache_service
        self._cache_ttl = 3600  # 1 hora
    
    def find_active_loans(self, user_id: str) -> List[Loan]:
        """
        Obtiene todos los préstamos activos del usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de préstamos activos
        """
        try:
            user_data = self._get_user_data(user_id)
            loans_data = user_data.get("prestamos_activos", [])
            
            loans = [Loan.from_dict(loan_data) for loan_data in loans_data]
            
            # Actualizar estados automáticamente
            for loan in loans:
                loan.actualizar_estado()
            
            return loans
            
        except Exception as e:
            logger.error(f"Error finding active loans for user {user_id}: {e}")
            return []
    
    def find_loan_history(self, user_id: str) -> List[Loan]:
        """
        Obtiene el historial completo de préstamos
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de todos los préstamos
        """
        try:
            user_data = self._get_user_data(user_id)
            
            # Combinar préstamos activos e históricos
            active_loans_data = user_data.get("prestamos_activos", [])
            history_loans_data = user_data.get("historial_prestamos", [])
            
            all_loans_data = active_loans_data + history_loans_data
            loans = [Loan.from_dict(loan_data) for loan_data in all_loans_data]
            
            # Ordenar por fecha de préstamo (más recientes primero)
            loans.sort(key=lambda l: l.fecha_prestamo or datetime.min, reverse=True)
            
            return loans
            
        except Exception as e:
            logger.error(f"Error finding loan history for user {user_id}: {e}")
            return []
    
    def find_by_book_id(self, user_id: str, book_id: str) -> Optional[Loan]:
        """
        Busca préstamo activo por ID del libro
        
        Args:
            user_id: ID del usuario
            book_id: ID del libro
        
        Returns:
            Préstamo encontrado o None
        """
        active_loans = self.find_active_loans(user_id)
        return next((loan for loan in active_loans if loan.libro_id == book_id), None)
    
    def find_by_title(self, user_id: str, title: str) -> Optional[Loan]:
        """
        Busca préstamo activo por título del libro
        
        Args:
            user_id: ID del usuario
            title: Título a buscar
        
        Returns:
            Préstamo encontrado o None
        """
        active_loans = self.find_active_loans(user_id)
        for loan in active_loans:
            if loan.coincide_titulo(title):
                return loan
        return None
    
    def save_loan(self, user_id: str, loan: Loan) -> None:
        """
        Guarda un préstamo (crear o actualizar)
        
        Args:
            user_id: ID del usuario
            loan: Préstamo a guardar
        """
        try:
            user_data = self._get_user_data(user_id)
            
            if loan.esta_activo():
                # Guardar como préstamo activo
                active_loans_data = user_data.get("prestamos_activos", [])
                
                # Buscar si ya existe
                loan_index = -1
                for i, existing_loan_data in enumerate(active_loans_data):
                    if existing_loan_data.get("id") == loan.id:
                        loan_index = i
                        break
                
                loan_dict = loan.to_dict()
                
                if loan_index >= 0:
                    active_loans_data[loan_index] = loan_dict
                    logger.info(f"Updated active loan {loan.id} for user {user_id}")
                else:
                    active_loans_data.append(loan_dict)
                    logger.info(f"Added new active loan {loan.id} for user {user_id}")
                
                user_data["prestamos_activos"] = active_loans_data
            else:
                # Mover a historial si no está activo
                self._move_to_history(user_data, loan)
            
            # Actualizar estadísticas
            self._update_loan_statistics(user_data)
            
            # Guardar datos
            self._save_user_data(user_id, user_data)
            
            # Invalidar cache
            self._invalidate_cache(user_id)
            
        except Exception as e:
            logger.error(f"Error saving loan {loan.id} for user {user_id}: {e}")
            raise
    
    def complete_loan(self, user_id: str, loan_id: str) -> bool:
        """
        Marca un préstamo como devuelto
        
        Args:
            user_id: ID del usuario
            loan_id: ID del préstamo
        
        Returns:
            True si se completó exitosamente
        """
        try:
            user_data = self._get_user_data(user_id)
            active_loans_data = user_data.get("prestamos_activos", [])
            
            # Buscar el préstamo activo
            loan_to_complete = None
            loan_index = -1
            
            for i, loan_data in enumerate(active_loans_data):
                if loan_data.get("id") == loan_id:
                    loan_to_complete = Loan.from_dict(loan_data)
                    loan_index = i
                    break
            
            if loan_to_complete is None:
                return False
            
            # Marcar como devuelto
            loan_to_complete.devolver()
            
            # Mover de activos a historial
            active_loans_data.pop(loan_index)
            user_data["prestamos_activos"] = active_loans_data
            
            # Agregar al historial
            history_loans_data = user_data.get("historial_prestamos", [])
            history_loans_data.append(loan_to_complete.to_dict())
            user_data["historial_prestamos"] = history_loans_data
            
            # Actualizar estadísticas
            stats = user_data.setdefault("estadisticas", {})
            stats["total_devoluciones"] = stats.get("total_devoluciones", 0) + 1
            
            # Guardar cambios
            self._save_user_data(user_id, user_data)
            self._invalidate_cache(user_id)
            
            logger.info(f"Completed loan {loan_id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error completing loan {loan_id} for user {user_id}: {e}")
            return False
    
    def _get_user_data(self, user_id: str) -> dict:
        """
        Método privado para obtener datos del usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Diccionario con datos del usuario
        """
        # Intentar cache primero
        cache_key = f"user_data_{user_id}"
        if self._cache_service:
            cached_data = self._cache_service.get(cache_key)
            if cached_data:
                return cached_data
        
        # Obtener estructura inicial por defecto
        initial_data = {
            "libros_disponibles": [],
            "prestamos_activos": [],
            "historial_prestamos": [],
            "estadisticas": {
                "total_libros": 0,
                "total_prestamos": 0,
                "total_devoluciones": 0
            }
        }
        
        # En implementación real, obtendría del data_adapter
        # Por ahora retornamos estructura inicial
        return initial_data
    
    def _save_user_data(self, user_id: str, user_data: dict) -> None:
        """
        Método privado para guardar datos del usuario
        
        Args:
            user_id: ID del usuario
            user_data: Datos a guardar
        """
        # En implementación real, usaría el data_adapter
        # Por ahora solo log
        logger.info(f"Saving user data for {user_id}")
    
    def _move_to_history(self, user_data: dict, loan: Loan) -> None:
        """
        Mueve un préstamo al historial
        
        Args:
            user_data: Datos del usuario
            loan: Préstamo a mover
        """
        # Remover de activos si existe
        active_loans = user_data.get("prestamos_activos", [])
        active_loans = [l for l in active_loans if l.get("id") != loan.id]
        user_data["prestamos_activos"] = active_loans
        
        # Agregar a historial
        history_loans = user_data.get("historial_prestamos", [])
        history_loans.append(loan.to_dict())
        user_data["historial_prestamos"] = history_loans
    
    def _update_loan_statistics(self, user_data: dict) -> None:
        """
        Actualiza estadísticas de préstamos
        
        Args:
            user_data: Datos del usuario
        """
        stats = user_data.setdefault("estadisticas", {})
        
        active_count = len(user_data.get("prestamos_activos", []))
        history_count = len(user_data.get("historial_prestamos", []))
        
        stats["prestamos_activos"] = active_count
        stats["total_prestamos"] = stats.get("total_prestamos", 0)
        
        # Si hay préstamos nuevos, incrementar total
        if active_count > 0:
            stats["total_prestamos"] = max(stats["total_prestamos"], active_count + history_count)
    
    def _invalidate_cache(self, user_id: str) -> None:
        """
        Invalida cache del usuario
        
        Args:
            user_id: ID del usuario
        """
        if self._cache_service:
            cache_key = f"user_data_{user_id}"
            self._cache_service.delete(cache_key)