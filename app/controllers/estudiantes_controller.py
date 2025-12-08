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

# 4. Cancelar (Eliminar lógicamente) una solicitud
@router.put("/solicitudes/{solicitud_id}/cancelar")
def cancelar_solicitud(solicitud_id: int, email_user: str, db: Session = Depends(database.get_db)):
    # Buscar usuario
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    # Buscar solicitud
    solicitud = db.query(models.Solicitud).filter(
        models.Solicitud.id == solicitud_id,
        models.Solicitud.estudiante_id == usuario.id
    ).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada o no te pertenece")
    
    # Cambio de estado (Logical Delete)
    solicitud.estado = "Cancelada"
    # Opcional: solicitud.is_active = False 
    
    db.commit()
    return {"mensaje": "Solicitud cancelada correctamente"}

# 5. Editar Solicitud
@router.put("/solicitudes/{solicitud_id}")
def editar_solicitud(solicitud_id: int, dto: schemas.SolicitudCreate, email_user: str, db: Session = Depends(database.get_db)):
    # Buscar usuario
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    # Buscar solicitud que pertenezca al usuario
    solicitud = db.query(models.Solicitud).filter(
        models.Solicitud.id == solicitud_id,
        models.Solicitud.estudiante_id == usuario.id
    ).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if solicitud.estado != "Abierta":
        raise HTTPException(status_code=400, detail="Solo puedes editar solicitudes Abiertas")

    # Actualizar campos
    solicitud.materia = dto.materia
    solicitud.tema = dto.tema
    solicitud.descripcion = dto.descripcion
    solicitud.fecha_limite = dto.fecha_limite
    solicitud.archivo_url = dto.archivo_url
    
    db.commit()
    db.refresh(solicitud)
    return solicitud

# 6. Solicitar ser Asesor (Crear Postulación)
@router.post("/postulacion")
def crear_postulacion(dto: schemas.PostulacionCreate, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    # Validar si ya existe una postulación previa
    existe = db.query(models.PostulacionAsesor).filter(models.PostulacionAsesor.usuario_id == usuario.id).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya tienes una solicitud en proceso o procesada.")

    nueva = models.PostulacionAsesor(**dto.dict(), usuario_id=usuario.id)
    nueva.estado = "Pendiente" # Forzamos estado inicial
    
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# 7. Aceptar una Oferta (Match)
@router.put("/solicitudes/{solicitud_id}/ofertas/{oferta_id}/aceptar")
def aceptar_oferta(solicitud_id: int, oferta_id: int, email_user: str, db: Session = Depends(database.get_db)):
    # 1. Validar que la solicitud sea del estudiante
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    solicitud = db.query(models.Solicitud).filter(
        models.Solicitud.id == solicitud_id,
        models.Solicitud.estudiante_id == usuario.id
    ).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if solicitud.estado != "Abierta":
        raise HTTPException(status_code=400, detail="Esta solicitud ya no está disponible para aceptar ofertas.")

    # 2. Validar que la oferta exista y sea de esa solicitud
    oferta_seleccionada = db.query(models.Oferta).filter(
        models.Oferta.id == oferta_id,
        models.Oferta.solicitud_id == solicitud_id
    ).first()

    if not oferta_seleccionada:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    # 3. APLICAR CAMBIOS (EL MATCH)
    
    # A) Solicitud pasa a EnProceso
    solicitud.estado = "EnProceso"
    
    # B) Oferta seleccionada pasa a Aceptada
    oferta_seleccionada.estado = "Aceptada"
    
    # C) Las demás ofertas se rechazan automáticamente
    otras_ofertas = db.query(models.Oferta).filter(
        models.Oferta.solicitud_id == solicitud_id,
        models.Oferta.id != oferta_id
    ).all()
    
    for of in otras_ofertas:
        of.estado = "Rechazada"

    db.commit()
    return {"mensaje": "Oferta aceptada. ¡La asesoría ha comenzado!"}

# 8. Finalizar la Asesoría (Cierre del ciclo)
@router.put("/solicitudes/{solicitud_id}/finalizar")
def finalizar_solicitud(solicitud_id: int, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    solicitud = db.query(models.Solicitud).filter(
        models.Solicitud.id == solicitud_id,
        models.Solicitud.estudiante_id == usuario.id
    ).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if solicitud.estado != "EnProceso":
        raise HTTPException(status_code=400, detail="Solo puedes finalizar asesorías que estén en proceso.")

    # 1. Finalizar la Solicitud
    solicitud.estado = "Finalizada"
    
    # 2. Finalizar también la Oferta Aceptada (NUEVO)
    oferta_ganadora = db.query(models.Oferta).filter(
        models.Oferta.solicitud_id == solicitud.id, 
        models.Oferta.estado == "Aceptada"
    ).first()
    
    if oferta_ganadora:
        oferta_ganadora.estado = "Finalizada"
    
    db.commit()
    return {"mensaje": "¡Felicidades! Asesoría completada con éxito."}