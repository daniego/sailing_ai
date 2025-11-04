from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

try:
    from .stepper import PRESET_STEPS, StepperError, controller as stepper_controller
except ImportError:  # pragma: no cover
    from stepper import PRESET_STEPS, StepperError, controller as stepper_controller  # type: ignore[no-redef]


class StepperCommand(BaseModel):
    direction: str
    rotation: str | None = None
    steps: int | None = None
    delay: float | None = None

# Create the FastAPI application
app = FastAPI(title="Sailing AI", version="0.1.0")

# --- Static files ---
# This will serve files from the local ./static directory at the /static URL path.
# Make sure you create a folder named "static" next to this app.py file (or adjust the path).
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Templates / Frontend ---
# This uses Jinja2 templates from the local ./templates directory.
# Create a folder named "templates" with an index.html file to render the homepage.
templates = Jinja2Templates(directory="templates")

# --- API Endpoints (JSON) ---
@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/items/{item_id}")
async def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "query": q}


@app.post("/api/stepper")
async def run_stepper(command: StepperCommand):
    direction = command.direction.lower()
    if direction not in ("clockwise", "counter-clockwise"):
        raise HTTPException(status_code=400, detail="direction must be 'clockwise' or 'counter-clockwise'")

    rotation = command.rotation.lower() if command.rotation else None
    steps = command.steps

    if steps is None:
        if rotation:
            preset = PRESET_STEPS.get(rotation)
            if preset is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"rotation must be one of {', '.join(sorted(PRESET_STEPS))}",
                )
            steps = preset
        else:
            steps = PRESET_STEPS["full"]
    elif steps <= 0:
        raise HTTPException(status_code=400, detail="steps must be a positive integer")

    kwargs = {}
    if command.delay is not None:
        if command.delay <= 0:
            raise HTTPException(status_code=400, detail="delay must be positive")
        kwargs["delay"] = command.delay

    try:
        await run_in_threadpool(stepper_controller.spin, direction, steps, **kwargs)
    except StepperError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:  # propagate GPIO issues
        raise HTTPException(status_code=500, detail="Stepper controller error") from exc

    return {
        "status": "ok",
        "direction": direction,
        "steps": steps,
        "rotation": rotation,
        **({"delay": kwargs["delay"]} if "delay" in kwargs else {}),
    }

# --- Frontend Route (HTML) ---
# Renders templates/index.html. You can add your JS/CSS under /static and reference them in the template.
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    # Additional context can be passed to the template via this dict
    context = {"request": request, "app_name": "Sailing AI"}
    return templates.TemplateResponse("index.html", context)

@app.get("/controls", response_class=HTMLResponse)
async def controls(request: Request):
    # Additional context can be passed to the template via this dict
    context = {"request": request, "app_name": "Sailing AI"}
    return templates.TemplateResponse("controls.html", context)

# Optional: custom 404 to return JSON for /api/* and HTML for others
@app.exception_handler(404)
async def not_found(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    # For non-API routes, try serving the homepage (useful for client-side routers)
    return templates.TemplateResponse("index.html", {"request": request}, status_code=404)

# Enable running with: python app.py
if __name__ == "__main__":
    import uvicorn
    # Host 0.0.0.0 so it's reachable in containers as well; change as needed
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
