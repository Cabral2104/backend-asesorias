from pydantic import BaseModel, EmailStr
from datetime import datetime

# ... (UsuarioCreate y UsuarioLogin se quedan igual) ...

class UsuarioCreate(BaseModel):
    nombre_completo: str
    email: EmailStr
    password: str

class UsuarioLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    rol: str
    nombre: str
    email: str

# Actualizamos la respuesta que se envía al cliente
class UsuarioResponse(BaseModel):
    id: int
    email: EmailStr
    nombre_completo: str
    rol: str
    is_active: bool       # <--- NUEVO
    created_at: datetime  # <--- NUEVO
    # modified_at: datetime # (Opcional si quieres mostrarlo)

    class Config:
        from_attributes = True