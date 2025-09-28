"""
Servicio de lógica de negocio para préstamos
Aplica los principios SOLID y maneja las reglas de negocio de préstamos
"""
from typing import List, Optional, Tuple
from datetime import datetime, timedelta

from interfaces.repository_interface import IBookRepository, ILoanRepository
from models.book import Book, BookStatus
from models.loan import Loan, LoanStatus
from helpers.utils import IdGenerator


class LoanService:
    """
    Servicio para manejar la lógica de negocio relacionada con préstamos
    
    Principios aplicados:
    - Single Responsibility: Solo lógica de negocio de préstamos
    - Dependency Inversion: Depende de abstracciones
    """

    def __init__(self, book_repository: IBookRepository, loan_repository: ILoanRepository, id_generator: IdGenerator = IdGenerator()):
        """
        Constructor con inyección de dependencias
        """
        self._book_repo = book_repository
        self._loan_repo = loan_repository
        self._id_generator = id_generator
        self._default_loan_days = 7
        self._max_loans_per_user = 10
    
    def create_loan(self, user_id: str, book_title: str = None, book_id: str = None, 
                   person_name: str = None, loan_days: int = None) -> Tuple[bool, str, Optional[Loan]]:
        """
        Crea un nuevo préstamo
        
        Args:
            user_id: ID del usuario
            book_title: Título del libro (opcional si se proporciona book_id)
            book_id: ID del libro (opcional si se proporciona book_title)
            person_name: Nombre de la persona (opcional)
            loan_days: Días de préstamo (opcional, default 7)
        
        Returns:
            Tuple[bool, str, Optional[Loan]]: (éxito, mensaje, préstamo creado)
        """
        # Buscar el libro
        book = None
        if book_id:
            book = self._book_repo.find_by_id(user_id, book_id)
        elif book_title:
            books = self._book_repo.find_by_title(user_id, book_title.strip())
            if len(books) == 1:
                book = books[0]
            elif len(books) > 1:
                # Múltiples coincidencias, necesita más especificidad
                titles = [f"'{b.titulo}'" for b in books[:3]]
                return False, f"Encontré varios libros: {', '.join(titles)}. Sé más específico", None
        
        if not book:
            return False, f"No encontré el libro '{book_title or book_id}'", None
        
        # Validar que el libro esté disponible
        existing_loan = self._loan_repo.find_by_book_id(user_id, book.id)
        if existing_loan and existing_loan.esta_activo():
            return False, f"'{book.titulo}' ya está prestado a {existing_loan.persona}", existing_loan
        
        # Validar límite de préstamos
        active_loans = self._loan_repo.find_active_loans(user_id)
        if len(active_loans) >= self._max_loans_per_user:
            return False, f"Has alcanzado el límite máximo de {self._max_loans_per_user} préstamos activos", None
        
        # Crear el préstamo
        days = loan_days or self._default_loan_days
        person = person_name.strip() if person_name and person_name.strip() else "un amigo"
        
        loan = Loan(
            id=self._id_generator.generate_loan_id(),
            libro_id=book.id,
            titulo=book.titulo,
            persona=person,
            fecha_prestamo=datetime.now(),
            fecha_limite=datetime.now() + timedelta(days=days),
            estado=LoanStatus.ACTIVO,
            dias_prestamo=days
        )
        
        # Actualizar el libro (incrementar contador de préstamos)
        book.prestar()
        
        # Guardar en repositorios
        self._loan_repo.save_loan(user_id, loan)
        self._book_repo.save(user_id, book)
        
        return True, f"Préstamo de '{book.titulo}' a {person} registrado exitosamente", loan
    
    def return_loan(self, user_id: str, book_title: str = None, loan_id: str = None) -> Tuple[bool, str, Optional[Loan]]:
        """
        Procesa la devolución de un préstamo
        
        Args:
            user_id: ID del usuario
            book_title: Título del libro (opcional si se proporciona loan_id)
            loan_id: ID del préstamo (opcional si se proporciona book_title)
        
        Returns:
            Tuple[bool, str, Optional[Loan]]: (éxito, mensaje, préstamo devuelto)
        """
        # Buscar el préstamo activo
        loan = None
        if loan_id:
            active_loans = self._loan_repo.find_active_loans(user_id)
            loan = next((l for l in active_loans if l.id == loan_id), None)
        elif book_title:
            loan = self._loan_repo.find_by_title(user_id, book_title.strip())
        
        if not loan or not loan.esta_activo():
            return False, f"No encontré un préstamo activo para '{book_title or loan_id}'", None
        
        # Marcar como devuelto
        loan.devolver()
        
        # Actualizar el libro como disponible
        book = self._book_repo.find_by_id(user_id, loan.libro_id)
        if book:
            book.devolver()
            self._book_repo.save(user_id, book)
        
        # Completar el préstamo
        self._loan_repo.complete_loan(user_id, loan.id)
        
        # Determinar si fue devuelto a tiempo
        on_time = loan.fue_devuelto_a_tiempo()
        time_msg = "a tiempo" if on_time else "un poco tarde"
        
        return True, f"Devolución de '{loan.titulo}' registrada {time_msg}", loan
    
    def get_active_loans(self, user_id: str) -> List[Loan]:
        """
        Obtiene todos los préstamos activos con estados actualizados
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de préstamos activos
        """
        loans = self._loan_repo.find_active_loans(user_id)
        
        # Actualizar estados (marcar vencidos si aplica)
        for loan in loans:
            loan.actualizar_estado()
        
        return loans
    
    def get_loan_history(self, user_id: str) -> List[Loan]:
        """
        Obtiene el historial completo de préstamos
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de todos los préstamos (activos e históricos)
        """
        return self._loan_repo.find_loan_history(user_id)
    
    def get_overdue_loans(self, user_id: str) -> List[Loan]:
        """
        Obtiene los préstamos vencidos
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Lista de préstamos vencidos
        """
        active_loans = self.get_active_loans(user_id)
        return [loan for loan in active_loans if loan.esta_vencido()]
    
    def get_loans_due_soon(self, user_id: str, days_threshold: int = 2) -> List[Loan]:
        """
        Obtiene préstamos que vencen pronto
        
        Args:
            user_id: ID del usuario
            days_threshold: Días de antelación para considerar "pronto" (default 2)
        
        Returns:
            Lista de préstamos que vencen en los próximos días
        """
        active_loans = self.get_active_loans(user_id)
        return [loan for loan in active_loans 
                if 0 <= loan.dias_restantes() <= days_threshold]
    
    def get_loan_statistics(self, user_id: str) -> dict:
        """
        Obtiene estadísticas de préstamos del usuario
        
        Args:
            user_id: ID del usuario
        
        Returns:
            Diccionario con estadísticas
        """
        all_loans = self.get_loan_history(user_id)
        active_loans = [l for l in all_loans if l.esta_activo()]
        completed_loans = [l for l in all_loans if l.estado == LoanStatus.DEVUELTO]
        
        # Estadísticas de puntualidad
        on_time_returns = [l for l in completed_loans if l.fue_devuelto_a_tiempo()]
        late_returns = [l for l in completed_loans if not l.fue_devuelto_a_tiempo()]
        
        # Personas que más piden libros
        person_count = {}
        for loan in all_loans:
            person = loan.persona
            person_count[person] = person_count.get(person, 0) + 1
        
        # Libro más prestado
        book_count = {}
        for loan in all_loans:
            title = loan.titulo
            book_count[title] = book_count.get(title, 0) + 1
        
        most_loaned_book = max(book_count.items(), key=lambda x: x[1]) if book_count else None
        most_frequent_borrower = max(person_count.items(), key=lambda x: x[1]) if person_count else None
        
        return {
            "total_loans": len(all_loans),
            "active_loans": len(active_loans),
            "completed_loans": len(completed_loans),
            "on_time_returns": len(on_time_returns),
            "late_returns": len(late_returns),
            "return_rate": len(on_time_returns) / len(completed_loans) if completed_loans else 0,
            "most_loaned_book": {
                "title": most_loaned_book[0],
                "times": most_loaned_book[1]
            } if most_loaned_book else None,
            "most_frequent_borrower": {
                "name": most_frequent_borrower[0],
                "loans": most_frequent_borrower[1]
            } if most_frequent_borrower else None,
            "overdue_loans": len([l for l in active_loans if l.esta_vencido()])
        }
    
    def extend_loan(self, user_id: str, loan_id: str, additional_days: int = 7) -> Tuple[bool, str, Optional[Loan]]:
        """
        Extiende la fecha límite de un préstamo
        
        Args:
            user_id: ID del usuario
            loan_id: ID del préstamo
            additional_days: Días adicionales (default 7)
        
        Returns:
            Tuple[bool, str, Optional[Loan]]: (éxito, mensaje, préstamo extendido)
        """
        active_loans = self.get_active_loans(user_id)
        loan = next((l for l in active_loans if l.id == loan_id), None)
        
        if not loan:
            return False, "Préstamo no encontrado o no está activo", None
        
        if additional_days <= 0:
            return False, "Los días adicionales deben ser positivos", loan
        
        # Extender fecha límite
        loan.fecha_limite += timedelta(days=additional_days)
        loan.dias_prestamo += additional_days
        
        # Guardar cambios
        self._loan_repo.save_loan(user_id, loan)
        
        new_date = loan.fecha_limite.strftime("%d de %B")
        return True, f"Préstamo de '{loan.titulo}' extendido hasta el {new_date}", loan
    