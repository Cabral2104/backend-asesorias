from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.mixins import AuditoriaMixin

# --- 1. SOLICITUD DE AYUDA (Lo que pide el estudiante) ---
class Solicitud(Base, AuditoriaMixin):
    __tablename__ = "Solicitudes"

    id = Column(Integer, primary_key=True, index=True)
    estudiante_id = Column(Integer, ForeignKey("Usuarios.id"), nullable=False)
    
    # Detalle del problema
    materia = Column(String(50), nullable=False)      # Ej: Matemáticas
    tema = Column(String(100), nullable=False)        # Ej: Cálculo Integral
    descripcion = Column(Text, nullable=False)        # Explicación larga
    fecha_limite = Column(DateTime, nullable=True)    # Para cuándo lo necesita
    archivo_url = Column(String(255), nullable=True)  # Link a Drive/Dropbox
    
    # Estado del flujo: 'Abierta', 'EnProceso', 'Finalizada', 'Cancelada'
    estado = Column(String(20), default="Abierta")

    # Relaciones
    estudiante = relationship("app.models.users.Usuario", back_populates="solicitudes")
    ofertas = relationship("Oferta", back_populates="solicitud")


# --- 2. OFERTA (La cotización del asesor) ---
class Oferta(Base, AuditoriaMixin):
    __tablename__ = "Ofertas"

    id = Column(Integer, primary_key=True, index=True)
    solicitud_id = Column(Integer, ForeignKey("Solicitudes.id"), nullable=False)
    asesor_id = Column(Integer, ForeignKey("Usuarios.id"), nullable=False)
    
    precio = Column(Float, nullable=False)            # Cuánto cobra
    mensaje = Column(Text, nullable=False)            # "Hola, puedo ayudarte..."
    
    # Estado de la oferta: 'Pendiente', 'Aceptada', 'Rechazada'
    estado = Column(String(20), default="Pendiente")

    # Relaciones
    solicitud = relationship("Solicitud", back_populates="ofertas")
    asesor = relationship("app.models.users.Usuario")


# --- 3. POSTULACIÓN (Para ser asesor) ---
class PostulacionAsesor(Base, AuditoriaMixin):
    __tablename__ = "PostulacionesAsesor"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("Usuarios.id"), unique=True)
    
    nivel_estudios = Column(String(50))               # Licenciatura, Maestría...
    institucion = Column(String(100))                 # Universidad
    especialidad = Column(String(100))                # Área fuerte
    experiencia = Column(Text)                        # Resumen curricular
    documento_url = Column(String(255))               # Link a CV/Certificados
    
    # Estado: 'Pendiente', 'Aprobado', 'Rechazado'
    estado = Column(String(20), default="Pendiente")

    usuario = relationship("app.models.users.Usuario", back_populates="postulacion")