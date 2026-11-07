from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from pathlib import Path
import os

DEFAULT_FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "dist" / "frontend" / "browser"

class SpaFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            return await super().get_response("index.html", scope)
    
def create_routes(app):
    frontend = Path(os.environ.get("BGOPL_FRONTEND_DIR") or DEFAULT_FRONTEND)
    if (frontend / "index.html").exists():
        app.mount("/app", SpaFiles(directory=str(frontend), html=True), name="app")
    return app