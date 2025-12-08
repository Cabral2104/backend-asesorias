from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine
# Importamos modelos para creación de tablas
from app.models import users, solicitudes 
# Importamos los controladores
from app.controllers import auth_controller, estudiantes_controller, mercado_controller, admin_controller, asesores_controller

# Crear tablas (Si borraste las anteriores, esto creará la nueva estructura completa)
users.Base.metadata.create_all(bind=engine)
solicitudes.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Lumina Lite API - Full MVC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REGISTRO DE RUTAS
app.include_router(auth_controller.router)
app.include_router(estudiantes_controller.router)
app.include_router(mercado_controller.router)
app.include_router(admin_controller.router)
app.include_router(asesores_controller.router)

@app.get("/")
def root():
    return {"message": "API Lumina Lite - Estructura Completa Lista"}