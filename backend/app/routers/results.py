from fastapi import APIRouter
from app.routers._combined import results_router, exports_router, logs_router

router = results_router
