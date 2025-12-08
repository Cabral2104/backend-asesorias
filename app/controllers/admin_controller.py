from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core import database
from app.models import solicitudes as models, users
from app.schemas import solicitudes as schemas

router = APIRouter(prefix="/admin", tags=["Administración"])

# 1. Ver Postulaciones Pendientes
@router.get("/postulaciones", response_model=list[schemas.PostulacionResponse])
def ver_postulaciones(db: Session = Depends(database.get_db)):
    # Traemos solo las pendientes para validar
    return db.query(models.PostulacionAsesor).filter(models.PostulacionAsesor.estado == "Pendiente").all()

# 2. Resolver Postulación (Aprobar o Rechazar)
@router.put("/postulaciones/{id}/resolver")
def resolver_postulacion(id: int, aprobada: bool, db: Session = Depends(database.get_db)):
    postulacion = db.query(models.PostulacionAsesor).get(id)
    if not postulacion:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")

    if aprobada:
        postulacion.estado = "Aprobado"
        
        # ¡LA MAGIA! Convertimos al usuario en Asesor automáticamente
        usuario = db.query(users.Usuario).get(postulacion.usuario_id)
        usuario.rol = "Asesor"
        
        mensaje = "Usuario ascendido a Asesor correctamente."
    else:
        postulacion.estado = "Rechazado"
        mensaje = "Postulación rechazada."

    db.commit()
    return {"mensaje": mensaje}

# 3. Stats Básicos (Para las gráficas del Dashboard)
@router.get("/stats")
def obtener_stats(db: Session = Depends(database.get_db)):
    total_usuarios = db.query(users.Usuario).count()
    total_solicitudes = db.query(models.Solicitud).count()
    solicitudes_abiertas = db.query(models.Solicitud).filter(models.Solicitud.estado == "Abierta").count()
    
    return {
        "usuarios": total_usuarios,
        "solicitudes_total": total_solicitudes,
        "solicitudes_activas": solicitudes_abiertas
    }