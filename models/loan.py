"""
Modelo de datos para Loan (Préstamo)
Implementa los principios de POO: Encapsulación y Abstracción
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional


class LoanStatus(Enum):
    """Estados posibles de un préstamo"""
    ACTIVO = "activo"
    DEVUELTO = "devuelto"
    VENCIDO = "vencido"


@dataclass
class Loan:
    """
    Modelo de datos para un préstamo
    
    Principios aplicados:
    - Encapsulación: Datos y comportamientos relacionados juntos
    - Single Responsibility: Solo representa un préstamo y sus operaciones
    """
    id: str
    libro_id: str
    titulo: str
    persona: str = "un amigo"
    fecha_prestamo: Optional[datetime] = None
    fecha_limite: Optional[datetime] = None
    fecha_devolucion: Optional[datetime] = None
    estado: LoanStatus = LoanStatus.ACTIVO
    dias_prestamo: int = 7
    
    def __post_init__(self):
        """Inicialización automática de campos después de creación"""
        if self.fecha_prestamo is None:
            self.fecha_prestamo = datetime.now()
        
        if self.fecha_limite is None:
            self.fecha_limite = self.fecha_prestamo + timedelta(days=self.dias_prestamo)
        
        # Normalizar strings
        self.titulo = self.titulo.strip()
        self.persona = self.persona.strip() if self.persona else "un amigo"
    
    def devolver(self) -> bool:
        """
        Marca el préstamo como devuelto
        Returns: True si se pudo devolver, False si ya estaba devuelto
        """
        if self.estado == LoanStatus.DEVUELTO:
            return False
        
        self.estado = LoanStatus.DEVUELTO
        self.fecha_devolucion = datetime.now()
        return True
    
    def esta_activo(self) -> bool:
        """Verifica si el préstamo está activo"""
        return self.estado == LoanStatus.ACTIVO
    
    def esta_vencido(self) -> bool:
        """Verifica si el préstamo está vencido"""
        if self.estado != LoanStatus.ACTIVO:
            return False
        return datetime.now() > self.fecha_limite
    
    def dias_restantes(self) -> int:
        """
        Calcula los días restantes para la devolución
        Returns: Número de días (negativo si está vencido)
        """
        if self.estado != LoanStatus.ACTIVO:
            return 0
        
        delta = self.fecha_limite - datetime.now()
        return delta.days
    
    def fue_devuelto_a_tiempo(self) -> bool:
        """
        Verifica si fue devuelto dentro del plazo
        Returns: True si fue a tiempo, False si fue tarde o está activo
        """
        if self.estado != LoanStatus.DEVUELTO or not self.fecha_devolucion:
            return False
        
        return self.fecha_devolucion <= self.fecha_limite
    
    def actualizar_estado(self):
        """Actualiza el estado basado en las fechas actuales"""
        if self.estado == LoanStatus.ACTIVO and self.esta_vencido():
            self.estado = LoanStatus.VENCIDO
    
    def coincide_titulo(self, busqueda: str) -> bool:
        """
        Verifica si el título del préstamo coincide con la búsqueda
        Args: busqueda - término a buscar (case insensitive)
        """
        if not busqueda:
            return False
        busqueda = busqueda.lower().strip()
        titulo = self.titulo.lower()
        return busqueda in titulo or titulo in busqueda
    
    def to_dict(self) -> dict:
        """Convierte el préstamo a diccionario para serialización"""
        return {
            "id": self.id,
            "libro_id": self.libro_id,
            "titulo": self.titulo,
            "persona": self.persona,
            "fecha_prestamo": self.fecha_prestamo.isoformat() if self.fecha_prestamo else None,
            "fecha_limite": self.fecha_limite.isoformat() if self.fecha_limite else None,
            "fecha_devolucion": self.fecha_devolucion.isoformat() if self.fecha_devolucion else None,
            "estado": self.estado.value,
            "dias_prestamo": self.dias_prestamo
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Loan':
        """
        Crea una instancia de Loan desde un diccionario
        Args: data - diccionario con los datos del préstamo
        """
        # Convertir fechas string a datetime
        fecha_prestamo = None
        fecha_limite = None
        fecha_devolucion = None
        
        for fecha_key, fecha_var in [
            ("fecha_prestamo", "fecha_prestamo"),
            ("fecha_limite", "fecha_limite"),
            ("fecha_devolucion", "fecha_devolucion")
        ]:
            fecha_str = data.get(fecha_key)
            if fecha_str:
                try:
                    if fecha_key == "fecha_prestamo":
                        fecha_prestamo = datetime.fromisoformat(fecha_str)
                    elif fecha_key == "fecha_limite":
                        fecha_limite = datetime.fromisoformat(fecha_str)
                    elif fecha_key == "fecha_devolucion":
                        fecha_devolucion = datetime.fromisoformat(fecha_str)
                except (ValueError, TypeError):
                    pass
        
        # Convertir estado string a enum
        estado_str = data.get("estado", "activo")
        estado = LoanStatus.ACTIVO
        try:
            estado = LoanStatus(estado_str)
        except ValueError:
            estado = LoanStatus.ACTIVO
        
        return cls(
            id=data.get("id", ""),
            libro_id=data.get("libro_id", ""),
            titulo=data.get("titulo", ""),
            persona=data.get("persona", "un amigo"),
            fecha_prestamo=fecha_prestamo,
            fecha_limite=fecha_limite,
            fecha_devolucion=fecha_devolucion,
            estado=estado,
            dias_prestamo=data.get("dias_prestamo", 7)
        )
    
    def __str__(self) -> str:
        """Representación string del préstamo"""
        return f"'{self.titulo}' prestado a {self.persona} ({self.estado.value})"