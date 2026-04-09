from app.api.auth import router as auth_router
from app.api.sources import router as sources_router
from app.api.articles import router as articles_router
from app.api.dashboard import router as dashboard_router
from app.api.scheduler import router as scheduler_router
from app.api.categories import router as categories_router
from app.api.youtube import router as youtube_router

all_routers = [
    auth_router,
    sources_router,
    articles_router,
    dashboard_router,
    scheduler_router,
    categories_router,
    youtube_router,
]
