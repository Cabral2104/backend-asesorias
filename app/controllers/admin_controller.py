from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import Optional

from app.core import database
from app.models import solicitudes as models, users

# Importamos los esquemas, incluyendo el nuevo de paginación
from app.schemas import solicitudes as schemas 

router = APIRouter(prefix="/admin", tags=["Administración"])

# ---------------------------------------------------------
# 1. VER POSTULACIONES PENDIENTES
# ---------------------------------------------------------
@router.get("/postulaciones", response_model=list[schemas.PostulacionResponse])
def ver_postulaciones(db: Session = Depends(database.get_db)):
    return db.query(models.PostulacionAsesor).filter(models.PostulacionAsesor.estado == "Pendiente").all()

# ---------------------------------------------------------
# 2. RESOLVER POSTULACIÓN
# ---------------------------------------------------------
@router.put("/postulaciones/{id}/resolver")
def resolver_postulacion(id: int, aprobada: bool, db: Session = Depends(database.get_db)):
    postulacion = db.query(models.PostulacionAsesor).get(id)
    if not postulacion:
        raise HTTPException(status_code=404, detail="Postulación no encontrada")

    if aprobada:
        postulacion.estado = "Aprobado"
        usuario = db.query(users.Usuario).get(postulacion.usuario_id)
        if usuario:
            usuario.rol = "Asesor"
            mensaje = "Usuario ascendido a Asesor correctamente."
        else:
            mensaje = "Postulación aprobada pero usuario no encontrado."
    else:
        postulacion.estado = "Rechazado"
        mensaje = "Postulación rechazada."

    db.commit()
    return {"mensaje": mensaje}

# ---------------------------------------------------------
# 3. STATS BÁSICOS
# ---------------------------------------------------------
@router.get("/stats")
def obtener_stats(db: Session = Depends(database.get_db)):
    total_usuarios = db.query(users.Usuario).count()
    total_solicitudes = db.query(models.Solicitud).count()
    # Ajusta los estados según tu lógica de negocio
    solicitudes_activas = db.query(models.Solicitud).filter(
        models.Solicitud.estado.in_(["Abierta", "Pendiente", "En Proceso"])
    ).count()
    
    return {
        "usuarios": total_usuarios,
        "solicitudes_total": total_solicitudes,
        "solicitudes_activas": solicitudes_activas
    }

# ---------------------------------------------------------
# 4. SOLICITUDES PAGINADAS (TABLA PRINCIPAL)
# ---------------------------------------------------------
@router.get("/solicitudes", response_model=schemas.PaginatedSolicitudesResponse)
def listar_solicitudes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    estado: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    offset = (page - 1) * limit
    
    # Query base
    query = db.query(models.Solicitud)
    
    # Filtro opcional
    if estado:
        query = query.filter(models.Solicitud.estado == estado)
    
    # Contar total
    total_records = query.count()
    
    # Calcular páginas
    total_pages = (total_records + limit - 1) // limit
    if total_pages == 0: 
        total_pages = 1

    # Obtener datos ordenados por ID descendente (lo más nuevo primero)
    data = query.order_by(desc(models.Solicitud.id))\
                .offset(offset)\
                .limit(limit)\
                .all()
    
    # Retornamos el diccionario que coincide con PaginatedSolicitudesResponse
    return {
        "data": data,
        "total": total_records,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }