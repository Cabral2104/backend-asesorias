from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core import database
from app.models import solicitudes as models, users
from app.schemas import solicitudes as schemas

router = APIRouter(prefix="/estudiantes", tags=["Estudiantes"])

# 1. Crear Solicitud
@router.post("/solicitudes", response_model=schemas.SolicitudResponse)
def crear_solicitud(dto: schemas.SolicitudCreate, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    nueva = models.Solicitud(**dto.dict(), estudiante_id=usuario.id)
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# 2. Ver MIS solicitudes (con ofertas recibidas)
@router.get("/mis-solicitudes", response_model=list[schemas.SolicitudResponse])
def mis_solicitudes(email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    # Traemos solicitudes ordenadas por fecha reciente
    solicitudes = db.query(models.Solicitud)\
        .filter(models.Solicitud.estudiante_id == usuario.id)\
        .order_by(models.Solicitud.created_at.desc())\
        .all()
    
    return solicitudes

# 3. Aceptar una oferta
@router.put("/solicitudes/{solicitud_id}/aceptar-oferta/{oferta_id}")
def aceptar_oferta(solicitud_id: int, oferta_id: int, db: Session = Depends(database.get_db)):
    # Validaciones
    solicitud = db.query(models.Solicitud).get(solicitud_id)
    oferta_ganadora = db.query(models.Oferta).get(oferta_id)
    
    if not solicitud or not oferta_ganadora:
        raise HTTPException(status_code=404, detail="No encontrado")
    
    if solicitud.estado != "Abierta":
        raise HTTPException(status_code=400, detail="La solicitud ya no está abierta")

    # Lógica Transaccional
    # 1. Marcar oferta ganadora
    oferta_ganadora.estado = "Aceptada"
    
    # 2. Marcar solicitud en proceso
    solicitud.estado = "EnProceso"
    
    # 3. Rechazar automáticamente las demás ofertas de esa solicitud
    otras_ofertas = db.query(models.Oferta).filter(
        models.Oferta.solicitud_id == solicitud_id,
        models.Oferta.id != oferta_id
    ).all()
    
    for o in otras_ofertas:
        o.estado = "Rechazada"
        
    db.commit()
    return {"mensaje": "Oferta aceptada exitosamente. El servicio ha comenzado."}