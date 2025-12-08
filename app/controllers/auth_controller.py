from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core import database, security
from app.models.users import Usuario
from app.schemas import auth as schemas

# Definimos el "Router" que actúa como controlador
router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post("/register", response_model=schemas.UsuarioResponse)
def register(usuario: schemas.UsuarioCreate, db: Session = Depends(database.get_db)):
    # Lógica de negocio: Validar existencia
    if db.query(Usuario).filter(Usuario.email == usuario.email).first():
        raise HTTPException(status_code=400, detail="El correo ya existe")
    
    # Crear modelo
    nuevo_usuario = Usuario(
        nombre_completo=usuario.nombre_completo,
        email=usuario.email,
        hashed_password=security.get_password_hash(usuario.password),
        rol="Estudiante" 
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@router.post("/login", response_model=schemas.Token)
def login(creds: schemas.UsuarioLogin, db: Session = Depends(database.get_db)):
    user = db.query(Usuario).filter(Usuario.email == creds.email).first()
    if not user or not security.verify_password(creds.password, user.hashed_password):
        raise HTTPException(status_code=404, detail="Credenciales inválidas")
    
    token = security.create_access_token({"sub": user.email, "rol": user.rol})
    return {
        "access_token": token,
        "token_type": "bearer",
        "rol": user.rol,
        "nombre": user.nombre_completo,
        "email": user.email
    }