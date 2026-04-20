"""
Capa de persistencia.
Estrategia: un fichero JSON por alumno en data/alumnos/<id>.json
"""

import os
import json

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALUMNOS_DIR = os.path.join(BASE_DIR, "data", "alumnos")


def _ruta(id_alumno: str) -> str:
    nombre = id_alumno.replace("/", "_").replace("\\", "_") + ".json"
    return os.path.join(ALUMNOS_DIR, nombre)


def cargar_alumno(id_alumno: str) -> dict | None:
    """Carga el perfil de un alumno. Devuelve None si no existe."""
    ruta = _ruta(id_alumno)
    if not os.path.exists(ruta):
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def guardar_alumno(alumno) -> bool:
    """Guarda el perfil de un alumno. Acepta objeto Pydantic o dict."""
    try:
        os.makedirs(ALUMNOS_DIR, exist_ok=True)
        id_alumno = (
            alumno.id_alumno if hasattr(alumno, "id_alumno")
            else alumno["id_alumno"]
        )
        datos = alumno.model_dump() if hasattr(alumno, "model_dump") else alumno
        with open(_ruta(id_alumno), "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        return True
    except IOError:
        return False


def listar_alumnos() -> list[str]:
    """Devuelve la lista de IDs de todos los alumnos registrados."""
    if not os.path.exists(ALUMNOS_DIR):
        return []
    return [
        f.replace(".json", "")
        for f in os.listdir(ALUMNOS_DIR)
        if f.endswith(".json")
    ]


def eliminar_alumno(id_alumno: str) -> bool:
    """Elimina el fichero de un alumno. Devuelve True si existía."""
    ruta = _ruta(id_alumno)
    if os.path.exists(ruta):
        os.remove(ruta)
        return True
    return False