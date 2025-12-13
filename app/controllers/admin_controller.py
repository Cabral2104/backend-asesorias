from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import desc, func, select
from typing import Optional, List
import io
import csv
import json
from xml.sax.saxutils import escape

# --- ReportLab Imports ---
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

from app.core import database
from app.models import solicitudes as models, users
from app.schemas import solicitudes as schemas

router = APIRouter(prefix="/admin", tags=["Administración"])

# ==============================================================================
#                                HELPERS
# ==============================================================================

def get_base_query(db: Session, estado: Optional[str] = None):
    """Query para la TABLA (UI), carga objetos completos."""
    query = db.query(models.Solicitud).options(
        selectinload(models.Solicitud.ofertas).joinedload(models.Oferta.asesor)
    )
    if estado:
        query = query.filter(models.Solicitud.estado == estado)
    return query.order_by(desc(models.Solicitud.created_at))

def get_fast_export_query(db: Session, estado: Optional[str] = None):
    """
    QUERY DE ALTA VELOCIDAD PARA EXPORTACIÓN.
    Selecciona solo las columnas necesarias (Tuplas) y cuenta en SQL.
    """
    # 1. Subconsulta para contar ofertas (rápido)
    ofertas_count = (
        select(func.count(models.Oferta.id))
        .where(models.Oferta.solicitud_id == models.Solicitud.id)
        .correlate(models.Solicitud)
        .scalar_subquery()
    )

    # 2. Selección de columnas específicas
    stmt = db.query(
        models.Solicitud.id,
        models.Solicitud.estudiante_id,
        models.Solicitud.tema,
        models.Solicitud.estado,
        models.Solicitud.created_at,
        models.Solicitud.descripcion, # Agregado para CSV
        ofertas_count.label("total_ofertas")
    )

    if estado:
        stmt = stmt.filter(models.Solicitud.estado == estado)
    
    return stmt.order_by(desc(models.Solicitud.created_at), desc(models.Solicitud.id))

# ==============================================================================
#                        1. GESTIÓN DE POSTULACIONES
# ==============================================================================
@router.get("/postulaciones", response_model=List[schemas.PostulacionResponse])
def ver_postulaciones(db: Session = Depends(database.get_db)):
    return db.query(models.PostulacionAsesor).filter(models.PostulacionAsesor.estado == "Pendiente").all()

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

# ==============================================================================
#                        2. ESTADÍSTICAS
# ==============================================================================
@router.get("/stats")
def obtener_stats(db: Session = Depends(database.get_db)):
    total_usuarios = db.query(func.count(users.Usuario.id)).scalar()
    total_solicitudes = db.query(func.count(models.Solicitud.id)).scalar()
    solicitudes_activas = db.query(func.count(models.Solicitud.id)).filter(
        models.Solicitud.estado.in_(["Abierta", "Pendiente", "En Proceso"])
    ).scalar()
    
    return {
        "usuarios": total_usuarios,
        "solicitudes_total": total_solicitudes,
        "solicitudes_activas": solicitudes_activas
    }

# ==============================================================================
#                        3. LISTADO PAGINADO (UI)
# ==============================================================================
@router.get("/solicitudes", response_model=schemas.PaginatedSolicitudesResponse)
def listar_solicitudes(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    estado: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    offset = (page - 1) * limit
    
    count_query = db.query(func.count(models.Solicitud.id))
    if estado:
        count_query = count_query.filter(models.Solicitud.estado == estado)
    
    total_records = count_query.scalar()
    total_pages = (total_records + limit - 1) // limit if total_records > 0 else 1

    data = get_base_query(db, estado).offset(offset).limit(limit).all()
    
    return {
        "data": data,
        "total": total_records,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }

# ==============================================================================
#                        4. EXPORTACIÓN ULTRARÁPIDA
# ==============================================================================

@router.get("/export/csv")
def export_csv(estado: Optional[str] = None, db: Session = Depends(database.get_db)):
    """Exporta CSV leyendo tuplas crudas."""
    def iter_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(["ID", "Estudiante ID", "Tema", "Descripción", "Estado", "Fecha Creación", "Ofertas"])
        yield output.getvalue()
        output.seek(0); output.truncate(0)

        query = get_fast_export_query(db, estado)
        batch_size = 1000
        offset = 0
        
        while True:
            # Trae una lista de TUPLAS.
            # Indices: 0=id, 1=estudiante_id, 2=tema, 3=estado, 4=created_at, 5=descripcion, 6=total_ofertas
            results = query.offset(offset).limit(batch_size).all()
            if not results:
                break
                
            for row in results:
                writer.writerow([
                    row[0], # id
                    row[1], # estudiante_id
                    row[2], # tema
                    row[5], # descripcion
                    row[3], # estado
                    row[4], # created_at
                    row[6]  # total_ofertas (ajustado indice por descripcion)
                ])
            
            yield output.getvalue()
            output.seek(0); output.truncate(0)
            offset += batch_size

    response = StreamingResponse(iter_csv(), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=reporte_{estado or 'full'}.csv"
    return response

@router.get("/export/json")
def export_json(estado: Optional[str] = None, db: Session = Depends(database.get_db)):
    """Exporta JSON streaming desde tuplas."""
    def iter_json():
        yield "[\n"
        query = get_fast_export_query(db, estado)
        batch_size = 1000
        offset = 0
        first = True
        
        while True:
            results = query.offset(offset).limit(batch_size).all()
            if not results:
                break
            
            for row in results:
                if not first: yield ",\n"
                else: first = False
                
                item = {
                    "id": row[0],
                    "estudiante_id": row[1],
                    "tema": row[2],
                    "estado": row[3],
                    "fecha": row[4].isoformat() if row[4] else None,
                    "ofertas": row[6]
                }
                yield json.dumps(item)
            
            offset += batch_size
        yield "\n]"

    response = StreamingResponse(iter_json(), media_type="application/json")
    response.headers["Content-Disposition"] = f"attachment; filename=reporte_{estado or 'full'}.json"
    return response

@router.get("/export/xml")
def export_xml(estado: Optional[str] = None, db: Session = Depends(database.get_db)):
    """Exporta XML streaming desde tuplas."""
    def iter_xml():
        yield '<?xml version="1.0" encoding="UTF-8"?>\n<solicitudes>\n'
        query = get_fast_export_query(db, estado)
        batch_size = 1000
        offset = 0
        
        while True:
            results = query.offset(offset).limit(batch_size).all()
            if not results:
                break
                
            for row in results:
                tema_safe = escape(row[2]) if row[2] else ""
                fecha_safe = row[4].isoformat() if row[4] else ""
                
                yield (
                    f'  <solicitud id="{row[0]}">\n'
                    f'    <estudiante_id>{row[1]}</estudiante_id>\n'
                    f'    <tema>{tema_safe}</tema>\n'
                    f'    <estado>{row[3]}</estado>\n'
                    f'    <fecha>{fecha_safe}</fecha>\n'
                    f'    <ofertas>{row[6]}</ofertas>\n'
                    f'  </solicitud>\n'
                )
            offset += batch_size
        yield '</solicitudes>'

    response = StreamingResponse(iter_xml(), media_type="application/xml")
    response.headers["Content-Disposition"] = f"attachment; filename=reporte_{estado or 'full'}.xml"
    return response

@router.get("/export/pdf")
def export_pdf(estado: Optional[str] = None, db: Session = Depends(database.get_db)):
    """
    PDF: Usa la query rápida y limita a 1000 registros para ser robusto.
    """
    # LÍMITE AUMENTADO A 1000 COMO SOLICITASTE
    limit_rows = 1000
    results = get_fast_export_query(db, estado).limit(limit_rows).all()
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter))
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph(f"Reporte de Solicitudes - {estado or 'Todas'}", styles['Title']))
    elements.append(Spacer(1, 20))
    
    # Gráfica
    counts = {"Abierta": 0, "En Proceso": 0, "Finalizada": 0, "Rechazada": 0}
    for row in results:
        st = row[3] # Index 3 es 'estado'
        if st in counts: counts[st] += 1

    data = [(counts["Abierta"], counts["En Proceso"], counts["Finalizada"], counts["Rechazada"])]
    drawing = Drawing(400, 150)
    bc = VerticalBarChart()
    bc.x = 50; bc.y = 20; bc.height = 100; bc.width = 300
    bc.data = data
    bc.strokeColor = colors.black
    bc.valueAxis.valueMin = 0
    bc.valueAxis.valueMax = max(max(data[0]) if data[0] else 0, 5) + 2
    bc.categoryAxis.categoryNames = ["Abierta", "Proceso", "Fin", "Rechazada"]
    drawing.add(bc)
    elements.append(drawing)
    elements.append(Spacer(1, 20))

    # Tabla
    table_rows = [['ID', 'Estudiante', 'Tema', 'Estado', 'Fecha', 'Ofertas']]
    for row in results:
        # Tuple: 0=id, 1=st_id, 2=tema, 3=estado, 4=date, 5=desc, 6=ofertas
        tema_corto = (row[2][:25] + '..') if row[2] and len(row[2]) > 25 else (row[2] or '')
        fecha_fmt = row[4].strftime("%Y-%m-%d") if row[4] else "-"
        
        table_rows.append([
            str(row[0]), 
            str(row[1]), 
            tema_corto,
            row[3],     
            fecha_fmt,
            str(row[6]) 
        ])
        
    t = Table(table_rows)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
        ('FONTSIZE', (0,0), (-1,-1), 8) # Letra más pequeña para que quepan
    ]))
    elements.append(t)
    
    if len(results) >= limit_rows:
        elements.append(Spacer(1, 10))
        elements.append(Paragraph(f"(Reporte limitado a los primeros {limit_rows} registros para optimizar el PDF)", styles['Italic']))

    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf", 
                             headers={"Content-Disposition": "attachment; filename=reporte.pdf"})