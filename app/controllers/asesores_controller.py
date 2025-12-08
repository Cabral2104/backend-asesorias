from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core import database
from app.models import solicitudes as models, users
from app.schemas import solicitudes as schemas

router = APIRouter(prefix="/asesores", tags=["Asesores"])

# 1. Ver solicitudes disponibles (Mercado)
@router.get("/mercado")
def ver_mercado(db: Session = Depends(database.get_db)):
    # Solo mostramos las que están "Abierta" y no están canceladas
    return db.query(models.Solicitud).filter(models.Solicitud.estado == "Abierta").all()

# 2. Crear una Oferta
@router.post("/ofertar")
def crear_oferta(dto: schemas.OfertaCreate, email_user: str, db: Session = Depends(database.get_db)):
    # Buscar al asesor
    asesor = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    if asesor.rol != "Asesor":
        raise HTTPException(status_code=403, detail="Solo los asesores pueden ofertar.")

    # Validar que no haya ofertado ya en esta solicitud
    existe = db.query(models.Oferta).filter(
        models.Oferta.solicitud_id == dto.solicitud_id,
        models.Oferta.asesor_id == asesor.id
    ).first()
    
    if existe:
        raise HTTPException(status_code=400, detail="Ya enviaste una oferta para esta solicitud.")

    nueva_oferta = models.Oferta(
        solicitud_id=dto.solicitud_id,
        asesor_id=asesor.id,
        precio=dto.precio,
        mensaje=dto.mensaje,
        estado="Pendiente"
    )
    
    db.add(nueva_oferta)
    db.commit()
    return {"mensaje": "Oferta enviada exitosamente"}

# 3. Ver mis ofertas enviadas (Historial)
@router.get("/mis-ofertas")
def mis_ofertas(email_user: str, db: Session = Depends(database.get_db)):
    asesor = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    # Traemos las ofertas del asesor
    return db.query(models.Oferta).filter(models.Oferta.asesor_id == asesor.id).all()