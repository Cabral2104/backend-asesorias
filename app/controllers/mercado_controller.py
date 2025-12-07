from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core import database
from app.models import solicitudes as models, users
from app.schemas import solicitudes as schemas

router = APIRouter(prefix="/mercado", tags=["Mercado Asesores"])

# 1. Postularse como Asesor
@router.post("/postulacion", response_model=schemas.PostulacionResponse)
def postularse(dto: schemas.PostulacionCreate, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    # Validar si ya existe
    existe = db.query(models.PostulacionAsesor).filter_by(usuario_id=usuario.id).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya tienes una postulación registrada")

    nueva = models.PostulacionAsesor(**dto.dict(), usuario_id=usuario.id)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# 2. Ver Mercado (Solicitudes Abiertas de OTROS estudiantes)
@router.get("/oportunidades", response_model=list[schemas.SolicitudResponse])
def ver_oportunidades(materia: str = None, db: Session = Depends(database.get_db)):
    query = db.query(models.Solicitud).filter(models.Solicitud.estado == "Abierta")
    
    if materia:
        query = query.filter(models.Solicitud.materia == materia)
        
    return query.all()

# 3. Enviar Oferta (Cotizar)
@router.post("/solicitud/{solicitud_id}/ofertar", response_model=schemas.OfertaResponse)
def enviar_oferta(solicitud_id: int, dto: schemas.OfertaCreate, email_asesor: str, db: Session = Depends(database.get_db)):
    asesor = db.query(users.Usuario).filter(users.Usuario.email == email_asesor).first()
    
    # Validar que no se auto-oferte
    solicitud = db.query(models.Solicitud).get(solicitud_id)
    if solicitud.estudiante_id == asesor.id:
        raise HTTPException(status_code=400, detail="No puedes ofertar en tu propia solicitud")

    nueva_oferta = models.Oferta(
        solicitud_id=solicitud_id,
        asesor_id=asesor.id,
        precio=dto.precio,
        mensaje=dto.mensaje
    )
    
    db.add(nueva_oferta)
    db.commit()
    db.refresh(nueva_oferta)
    
    # Mapeo manual para respuesta
    return {
        "id": nueva_oferta.id,
        "asesor_id": asesor.id,
        "nombre_asesor": asesor.nombre_completo,
        "precio": nueva_oferta.precio,
        "mensaje": nueva_oferta.mensaje,
        "estado": nueva_oferta.estado,
        "created_at": nueva_oferta.created_at
    }