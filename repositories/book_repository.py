"""
Repositorio para manejo de datos de libros
Aplica el patrón Repository y principios SOLID
"""
from typing import List, Optional
import logging

from interfaces.repository_interface import IBookRepository, IDataAdapter, ICacheService
from models.book import Book


logger = logging.getLogger(__name__)


class BookRepository(IBookRepository):
    """
    Implementación del repositorio de libros
    
    Principios aplicados:
    - Single Responsibility: Solo manejo de persistencia de libros
    - Dependency Inversion: Depende de abstracciones (IDataAdapter)
    - Interface Segregation: Implementa solo métodos necesarios
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
    
    def find_all(self, user_id: str) -> List[Book]:
        """
        Obtiene todos los libros del usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de libros
        """
        try:
            # Intentar obtener del cache primero
            cache_key = f"books_{user_id}"
            if self._cache_service:
                cached_data = self._cache_service.get(cache_key)
                if cached_data and "libros_disponibles" in cached_data:
                    logger.info(f"Cache hit for user books: {user_id}")
                    books_data = cached_data["libros_disponibles"]
                    return [Book.from_dict(book_data) for book_data in books_data]
            
            # Si no hay cache, obtener de persistencia
            user_data = self._get_user_data(user_id)
            books_data = user_data.get("libros_disponibles", [])
            books = [Book.from_dict(book_data) for book_data in books_data]
            
            # Guardar en cache si está disponible
            if self._cache_service:
                self._cache_service.set(cache_key, user_data, self._cache_ttl)
            
            return books
            
        except Exception as e:
            logger.error(f"Error finding all books for user {user_id}: {e}")
            return []
    
    def find_by_id(self, user_id: str, book_id: str) -> Optional[Book]:
        """
        Busca un libro por su ID
        
        Args:
            user_id: ID del usuario
            book_id: ID del libro
        
        Returns:
            Libro encontrado o None
        """
        books = self.find_all(user_id)
        return next((book for book in books if book.id == book_id), None)
    
    def find_by_title(self, user_id: str, title: str) -> List[Book]:
        """
        Busca libros por título (coincidencia parcial)
        
        Args:
            user_id: ID del usuario
            title: Título a buscar
        
        Returns:
            Lista de libros que coinciden
        """
        books = self.find_all(user_id)
        return [book for book in books if book.coincide_titulo(title)]
    
    def find_by_author(self, user_id: str, author: str) -> List[Book]:
        """
        Busca libros por autor (coincidencia parcial)
        
        Args:
            user_id: ID del usuario
            author: Autor a buscar
        
        Returns:
            Lista de libros que coinciden
        """
        books = self.find_all(user_id)
        return [book for book in books if book.coincide_autor(author)]
    
    def save(self, user_id: str, book: Book) -> None:
        """
        Guarda un libro (crear o actualizar)
        
        Args:
            user_id: ID del usuario
            book: Libro a guardar
        """
        try:
            user_data = self._get_user_data(user_id)
            books_data = user_data.get("libros_disponibles", [])
            
            # Buscar si el libro ya existe
            book_index = -1
            for i, existing_book_data in enumerate(books_data):
                if existing_book_data.get("id") == book.id:
                    book_index = i
                    break
            
            # Convertir libro a diccionario
            book_dict = book.to_dict()
            
            if book_index >= 0:
                # Actualizar libro existente
                books_data[book_index] = book_dict
                logger.info(f"Updated book {book.id} for user {user_id}")
            else:
                # Agregar nuevo libro
                books_data.append(book_dict)
                logger.info(f"Added new book {book.id} for user {user_id}")
            
            # Actualizar estadísticas
            stats = user_data.setdefault("estadisticas", {})
            stats["total_libros"] = len(books_data)
            
            # Guardar datos actualizados
            user_data["libros_disponibles"] = books_data
            self._save_user_data(user_id, user_data)
            
            # Invalidar cache
            if self._cache_service:
                cache_key = f"books_{user_id}"
                self._cache_service.delete(cache_key)
            
        except Exception as e:
            logger.error(f"Error saving book {book.id} for user {user_id}: {e}")
            raise
    
    def delete(self, user_id: str, book_id: str) -> bool:
        """
        Elimina un libro
        
        Args:
            user_id: ID del usuario
            book_id: ID del libro a eliminar
        
        Returns:
            True si se eliminó, False si no se encontró
        """
        try:
            user_data = self._get_user_data(user_id)
            books_data = user_data.get("libros_disponibles", [])
            
            # Buscar y eliminar el libro
            initial_count = len(books_data)
            books_data = [book_data for book_data in books_data 
                         if book_data.get("id") != book_id]
            
            if len(books_data) < initial_count:
                # Se eliminó el libro
                user_data["libros_disponibles"] = books_data
                
                # Actualizar estadísticas
                stats = user_data.setdefault("estadisticas", {})
                stats["total_libros"] = len(books_data)
                
                # Guardar cambios
                self._save_user_data(user_id, user_data)
                
                # Invalidar cache
                if self._cache_service:
                    cache_key = f"books_{user_id}"
                    self._cache_service.delete(cache_key)
                
                logger.info(f"Deleted book {book_id} for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deleting book {book_id} for user {user_id}: {e}")
            return False
    
    def exists_title(self, user_id: str, title: str) -> bool:
        """
        Verifica si existe un libro con ese título exacto
        
        Args:
            user_id: ID del usuario
            title: Título a verificar
        
        Returns:
            True si existe, False si no
        """
        books = self.find_all(user_id)
        normalized_title = title.lower().strip()
        return any(book.titulo.lower().strip() == normalized_title for book in books)
    
    def _get_user_data(self, user_id: str) -> dict:
        """
        Método privado para obtener datos del usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Diccionario con datos del usuario
        """
        # Este método sería implementado dependiendo del adaptador específico
        # Por ahora, simulamos la estructura esperada
        return {
            "libros_disponibles": [],
            "prestamos_activos": [],
            "historial_prestamos": [],
            "estadisticas": {
                "total_libros": 0,
                "total_prestamos": 0,
                "total_devoluciones": 0
            }
        }
    
    def _save_user_data(self, user_id: str, user_data: dict) -> None:
        """
        Método privado para guardar datos del usuario
        
        Args:
            user_id: ID del usuario
            user_data: Datos a guardar
        """
        # Este método sería implementado dependiendo del adaptador específico
        # La implementación real dependería del data_adapter inyectado
        pass