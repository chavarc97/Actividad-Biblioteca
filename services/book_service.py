"""
Servicio de lógica de negocio para libros
Aplica los principios SOLID y separa la lógica de negocio del acceso a datos
"""
import uuid
from typing import List, Optional, Tuple
from datetime import datetime

from interfaces.repository_interface import IBookRepository, ILoanRepository
from models.book import Book, BookStatus
from helpers.utils import IdGenerator


class BookService:
    """
    Servicio para manejar la lógica de negocio relacionada con libros
    
    Principios aplicados:
    - Single Responsibility: Solo lógica de negocio de libros
    - Dependency Inversion: Depende de abstracciones, no implementaciones
    - Open/Closed: Abierto para extensión, cerrado para modificación
    """
    
    def __init__(self, book_repository: IBookRepository, loan_repository: ILoanRepository, id_generator: IdGenerator = IdGenerator()):
        """
        Constructor con inyección de dependencias
        Args:
            book_repository: Repositorio de libros (abstracción)
            loan_repository: Repositorio de préstamos (abstracción)
        """
        self._book_repo = book_repository
        self._loan_repo = loan_repository
        self._id_generator = id_generator
    
    def add_book(self, user_id: str, titulo: str, autor: str = None, tipo: str = None) -> Tuple[bool, str, Optional[Book]]:
        """
        Agrega un nuevo libro a la colección
        
        Args:
            user_id: ID del usuario
            titulo: Título del libro (requerido)
            autor: Autor del libro (opcional)
            tipo: Tipo/género del libro (opcional)
        
        Returns:
            Tuple[bool, str, Optional[Book]]: (éxito, mensaje, libro creado)
        """
        # Validaciones de negocio
        if not titulo or not titulo.strip():
            return False, "El título es requerido", None
        
        titulo = titulo.strip()
        
        # Verificar si ya existe un libro con el mismo título
        if self._book_repo.exists_title(user_id, titulo):
            return False, f"Ya existe un libro con el título '{titulo}'", None
        
        # Normalizar datos opcionales
        autor = autor.strip() if autor and autor.strip() else "Desconocido"
        tipo = tipo.strip() if tipo and tipo.strip() else "Sin categoría"
        
        # Crear nuevo libro
        new_book = Book(
            id=self._id_generator.generate_unique_id(),
            titulo=titulo,
            autor=autor,
            tipo=tipo,
            fecha_agregado=datetime.now(),
            estado=BookStatus.DISPONIBLE,
            total_prestamos=0
        )
        
        # Guardar en repositorio
        self._book_repo.save(user_id, new_book)
        
        return True, f"Libro '{titulo}' agregado exitosamente", new_book
    
    def get_all_books(self, user_id: str) -> List[Book]:
        """
        Obtiene todos los libros del usuario con estados sincronizados
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de libros con estados actualizados
        """
        books = self._book_repo.find_all(user_id)
        
        # Sincronizar estados con préstamos activos
        active_loans = self._loan_repo.find_active_loans(user_id)
        loaned_book_ids = {loan.libro_id for loan in active_loans}
        
        for book in books:
            if book.id in loaned_book_ids:
                book.estado = BookStatus.PRESTADO
            else:
                book.estado = BookStatus.DISPONIBLE
        
        return books
    
    def search_books_by_title(self, user_id: str, search_term: str) -> List[Book]:
        """
        Busca libros por título (coincidencia parcial)
        
        Args:
            user_id: ID del usuario
            search_term: Término de búsqueda
        
        Returns:
            Lista de libros que coinciden con el término
        """
        if not search_term or not search_term.strip():
            return []
        
        books = self._book_repo.find_by_title(user_id, search_term.strip())
        return self._sync_book_states(user_id, books)
    
    def search_books_by_author(self, user_id: str, search_term: str) -> List[Book]:
        """
        Busca libros por autor (coincidencia parcial)
        
        Args:
            user_id: ID del usuario
            search_term: Término de búsqueda
        
        Returns:
            Lista de libros que coinciden con el autor
        """
        if not search_term or not search_term.strip():
            return []
        
        books = self._book_repo.find_by_author(user_id, search_term.strip())
        return self._sync_book_states(user_id, books)
    
    def get_available_books(self, user_id: str) -> List[Book]:
        """
        Obtiene solo los libros disponibles para préstamo
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de libros disponibles
        """
        all_books = self.get_all_books(user_id)
        return [book for book in all_books if book.esta_disponible()]
    
    def get_loaned_books(self, user_id: str) -> List[Book]:
        """
        Obtiene solo los libros que están prestados
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de libros prestados
        """
        all_books = self.get_all_books(user_id)
        return [book for book in all_books if not book.esta_disponible()]
    
    def delete_book(self, user_id: str, book_id: str = None, title: str = None) -> Tuple[bool, str, Optional[Book]]:
        """
        Elimina un libro de la colección
        
        Args:
            user_id: ID del usuario
            book_id: ID del libro (opcional)
            title: Título del libro (opcional)
        
        Returns:
            Tuple[bool, str, Optional[Book]]: (éxito, mensaje, libro eliminado)
        """
        # Buscar el libro
        book = None
        if book_id:
            book = self._book_repo.find_by_id(user_id, book_id)
        elif title:
            books = self._book_repo.find_by_title(user_id, title.strip())
            book = books[0] if books else None
        
        if not book:
            return False, "Libro no encontrado", None
        
        # Verificar si está prestado
        active_loan = self._loan_repo.find_by_book_id(user_id, book.id)
        if active_loan:
            return False, f"No se puede eliminar '{book.titulo}' porque está prestado a {active_loan.persona}", book
        
        # Eliminar del repositorio
        success = self._book_repo.delete(user_id, book.id)
        if success:
            return True, f"Libro '{book.titulo}' eliminado exitosamente", book
        else:
            return False, "Error al eliminar el libro", book
    
    def get_book_statistics(self, user_id: str) -> dict:
        """
        Obtiene estadísticas de los libros del usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Diccionario con estadísticas
        """
        books = self.get_all_books(user_id)
        available_books = [b for b in books if b.esta_disponible()]
        loaned_books = [b for b in books if not b.esta_disponible()]
        
        # Estadísticas por tipo
        types_count = {}
        authors_count = {}
        
        for book in books:
            # Contar por tipo
            book_type = book.tipo or "Sin categoría"
            types_count[book_type] = types_count.get(book_type, 0) + 1
            
            # Contar por autor
            author = book.autor or "Desconocido"
            authors_count[author] = authors_count.get(author, 0) + 1
        
        # Libro más prestado
        most_loaned = max(books, key=lambda b: b.total_prestamos) if books else None
        
        return {
            "total_books": len(books),
            "available_books": len(available_books),
            "loaned_books": len(loaned_books),
            "types_distribution": types_count,
            "authors_distribution": authors_count,
            "most_loaned_book": {
                "title": most_loaned.titulo,
                "author": most_loaned.autor,
                "times_loaned": most_loaned.total_prestamos
            } if most_loaned and most_loaned.total_prestamos > 0 else None
        }
    
    def _sync_book_states(self, user_id: str, books: List[Book]) -> List[Book]:
        """
        Método privado para sincronizar estados de libros con préstamos
        
        Args:
            user_id: ID del usuario
            books: Lista de libros a sincronizar
        
        Returns:
            Lista de libros con estados sincronizados
        """
        if not books:
            return books
        
        active_loans = self._loan_repo.find_active_loans(user_id)
        loaned_book_ids = {loan.libro_id for loan in active_loans}
        
        for book in books:
            if book.id in loaned_book_ids:
                book.estado = BookStatus.PRESTADO
            else:
                book.estado = BookStatus.DISPONIBLE
        
        return books