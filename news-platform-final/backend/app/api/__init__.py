from app.api.auth import router as auth_router
from app.api.sources import router as sources_router
from app.api.articles import router as articles_router
from app.api.dashboard import router as dashboard_router
from app.api.scheduler import router as scheduler_router
from app.api.categories import router as categories_router
from app.api.youtube import router as youtube_router
from app.api.polls import router as polls_router
from app.api.upload import router as upload_router
from app.api.wishes import router as wishes_router
from app.api.seo import router as seo_router

all_routers = [
    auth_router,
    sources_router,
    articles_router,
    dashboard_router,
    scheduler_router,
    categories_router,
    youtube_router,
    polls_router,
    upload_router,
    wishes_router,
    seo_router,
]
