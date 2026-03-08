from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.auth import router as auth_router
from app.api.routes.me import router as me_router
from app.api.routes.houses import router as houses_router
from app.api.routes.districts import router as districts_router
from app.api.routes.customer_profile import router as customer_profile_router
from app.api.routes.orders import router as orders_router
from app.api.routes.executor import router as executor_router
from app.api.routes.admin import router as admin_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(houses_router)
api_router.include_router(districts_router)
api_router.include_router(customer_profile_router)
api_router.include_router(orders_router)
api_router.include_router(executor_router)
api_router.include_router(admin_router)