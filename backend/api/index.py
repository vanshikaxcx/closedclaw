from __future__ import annotations

from fastapi import FastAPI

bootstrap_error: str | None = None

try:
	from app.main import app
except Exception as exc:  # pragma: no cover - defensive runtime guard for serverless bootstrap
	bootstrap_error = str(exc)
	app = FastAPI(title="ArthSetu Backend", version="1.0.0-degraded")

	@app.get("/")
	def root_status() -> dict[str, str | None]:
		return {
			"status": "degraded",
			"detail": "backend bootstrap failed",
			"error": bootstrap_error,
		}

	@app.get("/api/health")
	def degraded_health() -> dict[str, str | None]:
		return {
			"status": "degraded",
			"db": "unavailable",
			"detail": "backend bootstrap failed",
			"error": bootstrap_error,
		}
