from sqlalchemy import Column, DateTime, Boolean
from datetime import datetime

# Esta clase NO es una tabla, es una plantilla que otros modelos usarán
class AuditoriaMixin:
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    modified_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)