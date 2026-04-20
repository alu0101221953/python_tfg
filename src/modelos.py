"""
Modelos de datos.
Define las estructuras principales usando Pydantic para validación automática.
"""

from pydantic import BaseModel, Field
from datetime import datetime


class Traza(BaseModel):
    """Registro de una respuesta del alumno a un ejercicio."""
    id_pregunta: str
    correcta: bool
    categoria: int
    subcategoria: str = ""
    nivel: str
    tipo: str
    tiempo: int
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )


class Alumno(BaseModel):
    """Perfil completo de un alumno."""
    id_alumno: str
    nombre: str
    trazas: list[Traza] = []
    fecha_registro: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )

    def total_intentos(self) -> int:
        return len(self.trazas)

    def total_correctas(self) -> int:
        return sum(1 for t in self.trazas if t.correcta)

    def precision_global(self) -> float:
        if not self.trazas:
            return 0.0
        return round(self.total_correctas() / self.total_intentos() * 100, 1)

    def preguntas_vistas(self) -> set[str]:
        return {t.id_pregunta for t in self.trazas}


class RespuestaAlumno(BaseModel):
    """Payload enviado por el alumno al responder un ejercicio."""
    id_alumno: str
    id_pregunta: str
    respuesta: str
    tiempo: int = Field(default=0, ge=0)