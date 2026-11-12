import os
from pathlib import Path, PurePosixPath

from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

DEFAULT_FRONTEND = Path(__file__).resolve().parents[3] / "frontend" / "dist" / "frontend" / "browser"

class SpaFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or PurePosixPath(path).suffix:
                raise
            response = await super().get_response("index.html", scope)
        if path in ("", ".", "index.html") or not PurePosixPath(path).suffix:
            response.headers["Cache-Control"] = "no-cache"
        return response
    
def mount_routes(app) -> bool:
    frontend = Path(os.environ.get("BGOPL_FRONTEND_DIR") or DEFAULT_FRONTEND)
    built = (frontend / "index.html").exists()
    if built:
        app.mount("/app", SpaFiles(directory=str(frontend), html=True), name="app")

    target = "/app/" if built else "/docs"

    @app.get("/", include_in_schema=False)
    def root():
        return RedirectResponse(target)

    return built