"""
FastAPI application exposing Codex AOTGraph queries.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from neo4j import GraphDatabase

from src.api.models import ClassHierarchy, FieldAccessResponse, WhereUsedResponse
from src.api.queries import GraphQueryService
from src.config import Neo4jSettings, load_settings
from src.assistant import AssistantToolkit


def create_app(settings: Neo4jSettings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Codex AOTGraph API", version="0.1.0")
    templates = Jinja2Templates(
        directory=str(Path(__file__).resolve().parent.parent / "ui" / "templates")
    )
    @app.on_event("startup")
    def startup() -> None:
        driver = GraphDatabase.driver(
            settings.uri,
            auth=(settings.username, settings.password),
        )
        app.state.neo4j_driver = driver
        app.state.query_service = GraphQueryService(driver, database=settings.database)
        app.state.assistant = AssistantToolkit.from_defaults(
            settings=settings,
        )

    @app.on_event("shutdown")
    def shutdown() -> None:
        driver = getattr(app.state, "neo4j_driver", None)
        if driver:
            driver.close()
        assistant = getattr(app.state, "assistant", None)
        if assistant:
            assistant.close()

    def get_service() -> GraphQueryService:
        service = getattr(app.state, "query_service", None)
        if service is None:
            raise RuntimeError("Query service not initialized")
        return service

    def get_assistant() -> AssistantToolkit:
        assistant = getattr(app.state, "assistant", None)
        if assistant is None:
            raise RuntimeError("Assistant toolkit not initialized")
        return assistant

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/where-used/method", response_model=WhereUsedResponse)
    def where_used_method(
        class_name: str = Query(..., alias="className"),
        method_name: str = Query(..., alias="methodName"),
        model: str | None = Query(None),
        service: GraphQueryService = Depends(get_service),
    ) -> WhereUsedResponse:
        try:
            return service.where_used_method(class_name=class_name, method_name=method_name, model=model)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/field-access", response_model=FieldAccessResponse)
    def field_access(
        table_name: str = Query(..., alias="tableName"),
        field_name: str = Query(..., alias="fieldName"),
        model: str | None = Query(None),
        service: GraphQueryService = Depends(get_service),
    ) -> FieldAccessResponse:
        try:
            return service.field_access(table_name=table_name, field_name=field_name, model=model)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/class-hierarchy", response_model=ClassHierarchy)
    def class_hierarchy(
        class_name: str = Query(..., alias="className"),
        model: str | None = Query(None),
        service: GraphQueryService = Depends(get_service),
    ) -> ClassHierarchy:
        try:
            return service.class_hierarchy(class_name=class_name, model=model)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/explorer", response_class=HTMLResponse)
    def explorer(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("explorer.html", {"request": request})

    class AssistantSearchRequest(BaseModel):
        query: str
        label: str | None = None
        top_k: int = Field(5, alias="topK", ge=1, le=20)

    class AssistantExplainRequest(BaseModel):
        node_id: str = Field(..., alias="nodeId")

    class AssistantSourceRequest(BaseModel):
        method_id: str = Field(..., alias="methodId")

    @app.post("/assistant/search")
    def assistant_search(
        body: AssistantSearchRequest,
        assistant: AssistantToolkit = Depends(get_assistant),
    ):
        return assistant.search_nodes(body.query, top_k=body.top_k, label=body.label)

    @app.post("/assistant/explain")
    def assistant_explain(
        body: AssistantExplainRequest,
        assistant: AssistantToolkit = Depends(get_assistant),
    ):
        try:
            return assistant.explain_node(body.node_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post("/assistant/method-source")
    def assistant_method_source(
        body: AssistantSourceRequest,
        assistant: AssistantToolkit = Depends(get_assistant),
    ):
        try:
            return assistant.get_method_source(body.method_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/assistant", response_class=HTMLResponse)
    def assistant_ui(request: Request) -> HTMLResponse:
        return templates.TemplateResponse("assistant.html", {"request": request})

    return app


