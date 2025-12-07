from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core import database
from app.models.solicitudes import PostulacionAsesor
from app.models.users import Usuario
from app.schemas import solicitudes as schemas

router = APIRouter(prefix="/admin", tags=["Administración"])

@router.get("/asesores-pendientes", response_model=list[schemas.PostulacionResponse])
def ver_pendientes(db: Session = Depends(database.get_db)):
    return db.query(PostulacionAsesor).filter(PostulacionAsesor.estado == "Pendiente").all()

@router.put("/aprobar-asesor/{id_postulacion}")
def aprobar_asesor(id_postulacion: int, db: Session = Depends(database.get_db)):
    postulacion = db.query(PostulacionAsesor).get(id_postulacion)
    if not postulacion:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")
    
    # Aprobar y cambiar rol
    postulacion.estado = "Aprobado"
    usuario = db.query(Usuario).get(postulacion.usuario_id)
    usuario.rol = "Asesor"
    
    db.commit()
    return {"mensaje": f"Usuario {usuario.nombre_completo} ahora es ASESOR"}