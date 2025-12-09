from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

# --- OFERTAS (Primero, porque se usa dentro de Solicitud) ---
class OfertaCreate(BaseModel):
    solicitud_id: int
    precio: float
    mensaje: str

class OfertaResponse(BaseModel):
    id: int
    solicitud_id: int
    nombre_asesor: str
    precio: float
    mensaje: str
    estado: str
    created_at: datetime
    
    # NUEVO: Email del estudiante (solo visible si hay match)
    contacto_match: str | None = None 
    
    class Config:
        from_attributes = True

# --- SOLICITUDES (Lado Estudiante) ---
class SolicitudCreate(BaseModel):
    materia: str
    tema: str
    descripcion: str
    fecha_limite: datetime
    archivo_url: Optional[str] = None

class SolicitudResponse(SolicitudCreate):
    id: int
    estado: str
    estudiante_id: int
    created_at: datetime
    
    # NUEVO: Email del asesor (solo visible si hay match)
    contacto_match: str | None = None
    
    # Incluimos las ofertas recibidas
    ofertas: List[OfertaResponse] = []
    
    class Config:
        from_attributes = True

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