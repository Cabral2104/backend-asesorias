from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core import database
from app.models import solicitudes as models, users
from app.schemas import solicitudes as schemas

router = APIRouter(prefix="/asesores", tags=["Asesores"])

# 1. Ver Mercado
@router.get("/mercado")
def ver_mercado(db: Session = Depends(database.get_db)):
    return db.query(models.Solicitud).filter(models.Solicitud.estado == "Abierta").all()

# 2. Crear Oferta
@router.post("/ofertar")
def crear_oferta(dto: schemas.OfertaCreate, email_user: str, db: Session = Depends(database.get_db)):
    asesor = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    if asesor.rol != "Asesor":
        raise HTTPException(status_code=403, detail="Solo los asesores pueden ofertar.")

    existe = db.query(models.Oferta).filter(
        models.Oferta.solicitud_id == dto.solicitud_id,
        models.Oferta.asesor_id == asesor.id
    ).first()
    
    if existe:
        raise HTTPException(status_code=400, detail="Ya enviaste una oferta para esta solicitud.")

    nueva_oferta = models.Oferta(
        solicitud_id=dto.solicitud_id,
        asesor_id=asesor.id,
        # nombre_asesor lo omitimos al guardar porque no existe en la tabla
        precio=dto.precio,
        mensaje=dto.mensaje,
        estado="Pendiente"
    )
    
    db.add(nueva_oferta)
    db.commit()
    return {"mensaje": "Oferta enviada exitosamente"}

# 3. Mis Ofertas (CORREGIDO)
@router.get("/mis-ofertas", response_model=list[schemas.OfertaResponse])
def mis_ofertas(email_user: str, db: Session = Depends(database.get_db)):
    asesor = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    ofertas = db.query(models.Oferta).filter(models.Oferta.asesor_id == asesor.id).all()

    for of in ofertas:
        # A) RELLENAR NOMBRE (Corrección del Error)
        # Como soy yo mismo el asesor, uso mi propio nombre
        of.nombre_asesor = asesor.nombre_completo

        # B) LÓGICA DE CONTACTO
        if of.estado in ["Aceptada", "Finalizada"]:
            solicitud = db.query(models.Solicitud).filter(models.Solicitud.id == of.solicitud_id).first()
            if solicitud:
                estudiante = db.query(users.Usuario).filter(users.Usuario.id == solicitud.estudiante_id).first()
                if estudiante:
                    of.contacto_match = estudiante.email

    return ofertas