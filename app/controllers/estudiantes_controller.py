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
    
    nueva_solicitud = models.Solicitud(**dto.dict(), estudiante_id=usuario.id)
    nueva_solicitud.estado = "Abierta"
    
    db.add(nueva_solicitud)
    db.commit()
    db.refresh(nueva_solicitud)
    return nueva_solicitud

# 2. Ver Mis Solicitudes (CORREGIDO: Inyección de Nombres y Contacto)
@router.get("/mis-solicitudes", response_model=list[schemas.SolicitudResponse])
def mis_solicitudes(email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    solicitudes = db.query(models.Solicitud).filter(models.Solicitud.estudiante_id == usuario.id).all()
    
    for sol in solicitudes:
        # A) RELLENAR NOMBRE DEL ASESOR EN LAS OFERTAS (Corrección del Error)
        # Como la tabla Oferta ya no guarda el nombre, lo buscamos por el ID del asesor
        for oferta in sol.ofertas:
            if not hasattr(oferta, 'nombre_asesor') or not oferta.nombre_asesor:
                asesor_data = db.query(users.Usuario).filter(users.Usuario.id == oferta.asesor_id).first()
                if asesor_data:
                    oferta.nombre_asesor = asesor_data.nombre_completo
                else:
                    oferta.nombre_asesor = "Usuario Eliminado"

        # B) LÓGICA DE CONTACTO (Email cuando hay Match)
        if sol.estado in ["EnProceso", "Finalizada"]:
            # Buscamos la oferta ganadora
            oferta_ganadora = next((o for o in sol.ofertas if o.estado in ["Aceptada", "Finalizada"]), None)
            
            if oferta_ganadora:
                asesor = db.query(users.Usuario).filter(users.Usuario.id == oferta_ganadora.asesor_id).first()
                if asesor:
                    sol.contacto_match = asesor.email

    return solicitudes

# 3. Cancelar Solicitud
@router.put("/solicitudes/{solicitud_id}/cancelar")
def cancelar_solicitud(solicitud_id: int, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    solicitud = db.query(models.Solicitud).filter(
        models.Solicitud.id == solicitud_id,
        models.Solicitud.estudiante_id == usuario.id
    ).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    solicitud.estado = "Cancelada"
    db.commit()
    return {"mensaje": "Solicitud cancelada"}

# 4. Editar Solicitud
@router.put("/solicitudes/{solicitud_id}")
def editar_solicitud(solicitud_id: int, dto: schemas.SolicitudCreate, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    solicitud = db.query(models.Solicitud).filter(
        models.Solicitud.id == solicitud_id,
        models.Solicitud.estudiante_id == usuario.id
    ).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if solicitud.estado != "Abierta":
        raise HTTPException(status_code=400, detail="Solo puedes editar solicitudes Abiertas")

    solicitud.materia = dto.materia
    solicitud.tema = dto.tema
    solicitud.descripcion = dto.descripcion
    solicitud.fecha_limite = dto.fecha_limite
    solicitud.archivo_url = dto.archivo_url
    
    db.commit()
    db.refresh(solicitud)
    return solicitud

# 5. Solicitar ser Asesor (Postulación)
@router.post("/postulacion")
def crear_postulacion(dto: schemas.PostulacionCreate, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    
    existe = db.query(models.PostulacionAsesor).filter(models.PostulacionAsesor.usuario_id == usuario.id).first()
    if existe:
        raise HTTPException(status_code=400, detail="Ya tienes una solicitud en proceso.")

    nueva = models.PostulacionAsesor(**dto.dict(), usuario_id=usuario.id)
    nueva.estado = "Pendiente"
    
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

# 6. Aceptar Oferta (Match)
@router.put("/solicitudes/{solicitud_id}/ofertas/{oferta_id}/aceptar")
def aceptar_oferta(solicitud_id: int, oferta_id: int, email_user: str, db: Session = Depends(database.get_db)):
    usuario = db.query(users.Usuario).filter(users.Usuario.email == email_user).first()
    solicitud = db.query(models.Solicitud).filter(
        models.Solicitud.id == solicitud_id,
        models.Solicitud.estudiante_id == usuario.id
    ).first()

    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    
    if solicitud.estado != "Abierta":
        raise HTTPException(status_code=400, detail="Esta solicitud ya no está disponible.")

    oferta_seleccionada = db.query(models.Oferta).filter(
        models.Oferta.id == oferta_id,
        models.Oferta.solicitud_id == solicitud_id
    ).first()

    if not oferta_seleccionada:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    # Match
    solicitud.estado = "EnProceso"
    oferta_seleccionada.estado = "Aceptada"
    
    otras_ofertas = db.query(models.Oferta).filter(
        models.Oferta.solicitud_id == solicitud_id,
        models.Oferta.id != oferta_id
    ).all()
    
    for of in otras_ofertas:
        of.estado = "Rechazada"

    db.commit()
    return {"mensaje": "Oferta aceptada."}

# 7. Finalizar Asesoría
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
        raise HTTPException(status_code=400, detail="Solo puedes finalizar asesorías en proceso.")

    solicitud.estado = "Finalizada"
    
    oferta_ganadora = db.query(models.Oferta).filter(
        models.Oferta.solicitud_id == solicitud.id, 
        models.Oferta.estado == "Aceptada"
    ).first()
    
    if oferta_ganadora:
        oferta_ganadora.estado = "Finalizada"
    
    db.commit()
    return {"mensaje": "Asesoría finalizada."}