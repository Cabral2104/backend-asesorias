from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.mixins import AuditoriaMixin  # <--- IMPORTAMOS EL MIXIN

# Heredamos de Base (SQLAlchemy) Y de AuditoriaMixin (Nuestros campos)
class Usuario(Base, AuditoriaMixin):
    __tablename__ = "Usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nombre_completo = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(200), nullable=False)
    rol = Column(String(20), default="Estudiante")
    
    # NOTA: created_at, modified_at e is_active se inyectan automáticamente aquí

    # Relaciones
    solicitudes = relationship("app.models.solicitudes.Solicitud", back_populates="estudiante")
    postulacion = relationship("app.models.solicitudes.PostulacionAsesor", back_populates="usuario", uselist=False)