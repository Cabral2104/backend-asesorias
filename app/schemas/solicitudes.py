from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime
from typing import List, Optional

# --- OFERTAS ---
class OfertaCreate(BaseModel):
    solicitud_id: int
    precio: float
    mensaje: str

class OfertaResponse(BaseModel):
    id: int
    solicitud_id: int
    # Lo hacemos opcional para evitar el crash si no se ha hecho el join con el usuario
    nombre_asesor: Optional[str] = None 
    precio: float
    mensaje: str
    estado: str
    created_at: datetime
    
    contacto_match: Optional[str] = None 
    
    model_config = ConfigDict(from_attributes=True)

# --- SOLICITUDES ---
class SolicitudCreate(BaseModel):
    materia: str
    tema: str
    descripcion: str
    fecha_limite: datetime
    archivo_url: Optional[str] = None

class SolicitudResponse(SolicitudCreate):
    id: int
    estado: str
    
    # CORRECCIÓN: Usamos estudiante_id que es como se llama en tu BD usualmente
    estudiante_id: int 
    
    created_at: Optional[datetime] = None
    
    contacto_match: Optional[str] = None
    
    ofertas: List[OfertaResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

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
    
    model_config = ConfigDict(from_attributes=True)

# --- PAGINACIÓN ---
class PaginatedSolicitudesResponse(BaseModel):
    data: List[SolicitudResponse]
    total: int
    page: int
    limit: int
    total_pages: int