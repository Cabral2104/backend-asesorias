from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import List, Optional

# --- DTOs COMUNES ---
class OfertaResponse(BaseModel):
    id: int
    asesor_id: int
    nombre_asesor: str = "Asesor" # Campo calculado (se llenará en el controller)
    precio: float
    mensaje: str
    estado: str
    created_at: datetime
    class Config:
        from_attributes = True

# --- SOLICITUDES (Lado Estudiante) ---
class SolicitudCreate(BaseModel):
    materia: str
    tema: str
    descripcion: str
    fecha_limite: datetime
    archivo_url: Optional[str] = None # String simple para evitar errores de validación URL estrictos

class SolicitudResponse(SolicitudCreate):
    id: int
    estado: str
    estudiante_id: int
    created_at: datetime
    # Incluimos las ofertas para que el estudiante vea quién le cotizó
    ofertas: List[OfertaResponse] = []
    
    class Config:
        from_attributes = True

# --- OFERTAS (Lado Asesor) ---
class OfertaCreate(BaseModel):
    precio: float
    mensaje: str

# --- POSTULACIÓN ASESOR ---
class PostulacionCreate(BaseModel):
    nivel_estudios: str
    institucion: str
    especialidad: str
    experiencia: str
    documento_url: str

class PostulacionResponse(PostulacionCreate):
    id: int
    estado: str
    usuario_id: int
    created_at: datetime
    class Config:
        from_attributes = True