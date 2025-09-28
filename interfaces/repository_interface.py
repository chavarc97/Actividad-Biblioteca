"""
Interfaces para los repositorios
Aplica el principio de Dependency Inversion y Interface Segregation
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from models.book import Book
from models.loan import Loan


class IDataAdapter(ABC):
    """
    Interfaz para adaptadores de persistencia
    Principio de Interface Segregation: Solo métodos esenciales
    """
    
    @abstractmethod
    def get_attributes(self, request_envelope) -> Dict[str, Any]:
        """Obtiene atributos persistentes del usuario"""
        pass
    
    @abstractmethod
    def save_attributes(self, request_envelope, attributes: Dict[str, Any]) -> None:
        """Guarda atributos persistentes del usuario"""
        pass
    
    @abstractmethod
    def delete_attributes(self, request_envelope) -> None:
        """Elimina todos los atributos del usuario"""
        pass


class IBookRepository(ABC):
    """
    Interfaz para repositorio de libros
    Principio de Single Responsibility: Solo operaciones con libros
    """
    
    @abstractmethod
    def find_all(self, user_id: str) -> List[Book]:
        """Obtiene todos los libros del usuario"""
        pass
    
    @abstractmethod
    def find_by_id(self, user_id: str, book_id: str) -> Optional[Book]:
        """Busca un libro por su ID"""
        pass
    
    @abstractmethod
    def find_by_title(self, user_id: str, title: str) -> List[Book]:
        """Busca libros por título (coincidencia parcial)"""
        pass
    
    @abstractmethod
    def find_by_author(self, user_id: str, author: str) -> List[Book]:
        """Busca libros por autor (coincidencia parcial)"""
        pass
    
    @abstractmethod
    def save(self, user_id: str, book: Book) -> None:
        """Guarda un libro"""
        pass
    
    @abstractmethod
    def delete(self, user_id: str, book_id: str) -> bool:
        """Elimina un libro. Returns True si se eliminó"""
        pass
    
    @abstractmethod
    def exists_title(self, user_id: str, title: str) -> bool:
        """Verifica si existe un libro con ese título exacto"""
        pass


class ILoanRepository(ABC):
    """
    Interfaz para repositorio de préstamos
    Principio de Single Responsibility: Solo operaciones con préstamos
    """
    
    @abstractmethod
    def find_active_loans(self, user_id: str) -> List[Loan]:
        """Obtiene todos los préstamos activos"""
        pass
    
    @abstractmethod
    def find_loan_history(self, user_id: str) -> List[Loan]:
        """Obtiene el historial completo de préstamos"""
        pass
    
    @abstractmethod
    def find_by_book_id(self, user_id: str, book_id: str) -> Optional[Loan]:
        """Busca préstamo activo por ID del libro"""
        pass
    
    @abstractmethod
    def find_by_title(self, user_id: str, title: str) -> Optional[Loan]:
        """Busca préstamo activo por título del libro"""
        pass
    
    @abstractmethod
    def save_loan(self, user_id: str, loan: Loan) -> None:
        """Guarda un préstamo"""
        pass
    
    @abstractmethod
    def complete_loan(self, user_id: str, loan_id: str) -> bool:
        """Marca un préstamo como devuelto. Returns True si se completó"""
        pass


class ICacheService(ABC):
    """
    Interfaz para servicio de cache
    Principio de Interface Segregation: Solo operaciones de cache
    """
    
    @abstractmethod
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos del cache"""
        pass
    
    @abstractmethod
    def set(self, key: str, data: Dict[str, Any], ttl_seconds: int = 3600) -> None:
        """Guarda datos en cache con TTL"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        """Elimina datos del cache"""
        pass
    
    @abstractmethod
    def clear_all(self) -> None:
        """Limpia todo el cache"""
        pass