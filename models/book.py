"""
Modelo de datos para Book (Libro)
Implementa los principios de POO: Encapsulación y Abstracción
"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class BookStatus(Enum):
    """Estados posibles de un libro"""
    DISPONIBLE = "disponible"
    PRESTADO = "prestado"


@dataclass
class Book:
    """
    Modelo de datos para un libro
    
    Principios aplicados:
    - Encapsulación: Datos y comportamientos relacionados juntos
    - Single Responsibility: Solo representa un libro y sus propiedades
    """
    id: str
    titulo: str
    autor: str = "Desconocido"
    tipo: str = "Sin categoría"
    fecha_agregado: Optional[datetime] = None
    estado: BookStatus = BookStatus.DISPONIBLE
    total_prestamos: int = 0
    
    def __post_init__(self):
        """Inicialización automática de campos después de creación"""
        if self.fecha_agregado is None:
            self.fecha_agregado = datetime.now()
        
        # Normalizar strings
        self.titulo = self.titulo.strip()
        self.autor = self.autor.strip() if self.autor else "Desconocido"
        self.tipo = self.tipo.strip() if self.tipo else "Sin categoría"
    
    def prestar(self) -> bool:
        """
        Marca el libro como prestado
        Returns: True si se pudo prestar, False si ya estaba prestado
        """
        if self.estado == BookStatus.PRESTADO:
            return False
        
        self.estado = BookStatus.PRESTADO
        self.total_prestamos += 1
        return True
    
    def devolver(self) -> bool:
        """
        Marca el libro como disponible
        Returns: True si se pudo devolver, False si ya estaba disponible
        """
        if self.estado == BookStatus.DISPONIBLE:
            return False
        
        self.estado = BookStatus.DISPONIBLE
        return True
    
    def esta_disponible(self) -> bool:
        """Verifica si el libro está disponible para préstamo"""
        return self.estado == BookStatus.DISPONIBLE
    
    def coincide_titulo(self, busqueda: str) -> bool:
        """
        Verifica si el título coincide con la búsqueda
        Args: busqueda - término a buscar (case insensitive)
        """
        if not busqueda:
            return False
        busqueda = busqueda.lower().strip()
        titulo = self.titulo.lower()
        return busqueda in titulo or titulo in busqueda
    
    def coincide_autor(self, busqueda: str) -> bool:
        """
        Verifica si el autor coincide con la búsqueda
        Args: busqueda - término a buscar (case insensitive)
        """
        if not busqueda:
            return False
        busqueda = busqueda.lower().strip()
        autor = self.autor.lower()
        return busqueda in autor or autor in busqueda
    
    def to_dict(self) -> dict:
        """Convierte el libro a diccionario para serialización"""
        return {
            "id": self.id,
            "titulo": self.titulo,
            "autor": self.autor,
            "tipo": self.tipo,
            "fecha_agregado": self.fecha_agregado.isoformat() if self.fecha_agregado else None,
            "estado": self.estado.value,
            "total_prestamos": self.total_prestamos
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Book':
        """
        Crea una instancia de Book desde un diccionario
        Args: data - diccionario con los datos del libro
        """
        fecha_str = data.get("fecha_agregado")
        fecha_agregado = None
        if fecha_str:
            try:
                fecha_agregado = datetime.fromisoformat(fecha_str)
            except (ValueError, TypeError):
                fecha_agregado = datetime.now()
        
        # Convertir estado string a enum
        estado_str = data.get("estado", "disponible")
        estado = BookStatus.DISPONIBLE
        try:
            estado = BookStatus(estado_str)
        except ValueError:
            estado = BookStatus.DISPONIBLE
        
        return cls(
            id=data.get("id", ""),
            titulo=data.get("titulo", ""),
            autor=data.get("autor", "Desconocido"),
            tipo=data.get("tipo", "Sin categoría"),
            fecha_agregado=fecha_agregado,
            estado=estado,
            total_prestamos=data.get("total_prestamos", 0)
        )
    
    def __str__(self) -> str:
        """Representación string del libro"""
        return f"'{self.titulo}' por {self.autor} ({self.estado.value})"