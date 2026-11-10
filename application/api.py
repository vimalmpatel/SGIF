"""Keycloak-protected SGIF API for a local lab deployment."""

import hashlib
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Annotated, Any, Literal

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, create_engine, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from application.event_ingest import iter_normalized_events


MAX_IMPORT_CHARS = 1_000_000
MAX_IMPORT_EVENTS = 1_000
BEARER = HTTPBearer(auto_error=False)


class Base(DeclarativeBase):
    pass


class Asset(Base):
    __tablename__ = "assets"

    asset_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(80), nullable=False)
    zone: Mapped[str] = mapped_column(String(80), nullable=False)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (UniqueConstraint("event_hash", name="uq_events_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    observed_at: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sensor: Mapped[str | None] = mapped_column(String(200))
    src_ip: Mapped[str | None] = mapped_column(String(45))
    src_port: Mapped[int | None] = mapped_column(Integer)
    dest_ip: Mapped[str | None] = mapped_column(String(45))
    dest_port: Mapped[int | None] = mapped_column(Integer)
    protocol: Mapped[str | None] = mapped_column(String(20))


class AuditRecord(Base):
    __tablename__ = "audit_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor_sub: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    details: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Principal(BaseModel):
    subject: str
    roles: set[str]


class AssetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=1, max_length=200)
    asset_type: str = Field(min_length=1, max_length=80)
    zone: str = Field(min_length=1, max_length=80)
    criticality: Literal["low", "moderate", "high", "critical"]
    owner: str = Field(min_length=1, max_length=120)


class EventImport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source: Literal["wazuh", "suricata", "zeek"]
    content: str = Field(min_length=1, max_length=MAX_IMPORT_CHARS)


def _database_url() -> str:
    return os.getenv("DATABASE_URL", "sqlite:///./sgif.db")


def get_session(request: Request):
    with request.app.state.session_factory() as session:
        yield session


def current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)],
    request: Request,
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    try:
        signing_key = request.app.state.jwks_client.get_signing_key_from_jwt(credentials.credentials)
        claims = jwt.decode(
            credentials.credentials,
            signing_key.key,
            algorithms=["RS256"],
            audience=request.app.state.oidc_audience,
            issuer=request.app.state.oidc_issuer,
            leeway=30,
        )
    except (jwt.PyJWTError, OSError) as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token") from error

    realm_access = claims.get("realm_access", {})
    roles = realm_access.get("roles", []) if isinstance(realm_access, dict) else []
    if not isinstance(roles, list) or not all(isinstance(role, str) for role in roles):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid role claims")
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid subject claim")
    return Principal(subject=subject, roles=set(roles))


def require_roles(*allowed_roles: str):
    def dependency(principal: Annotated[Principal, Depends(current_principal)]) -> Principal:
        if not principal.roles.intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return principal

    return dependency


def create_app(database_url: str | None = None) -> FastAPI:
    resolved_database_url = database_url or _database_url()
    engine_options: dict[str, Any] = {"pool_pre_ping": True}
    if resolved_database_url.startswith("sqlite"):
        engine_options["connect_args"] = {"check_same_thread": False}
        if resolved_database_url in {"sqlite://", "sqlite:///:memory:"}:
            engine_options["poolclass"] = StaticPool
    engine = create_engine(resolved_database_url, **engine_options)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        Base.metadata.create_all(bind=engine)
        yield
        engine.dispose()

    app = FastAPI(
        title="SGIF API",
        version="0.1.0",
        docs_url=None if os.getenv("APP_ENV") == "production" else "/docs",
        lifespan=lifespan,
    )
    app.state.session_factory = session_factory
    app.state.jwks_uri = os.getenv(
        "OIDC_JWKS_URI",
        "http://localhost:8080/realms/sgif-lab/protocol/openid-connect/certs",
    )
    app.state.oidc_issuer = os.getenv("OIDC_ISSUER", "http://localhost:8080/realms/sgif-lab")
    app.state.oidc_audience = os.getenv("OIDC_AUDIENCE", "sgif-api")
    app.state.jwks_client = PyJWKClient(app.state.jwks_uri, cache_jwk_set=True, lifespan=300)

    cors_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/healthz")
    def health(session: Annotated[Session, Depends(get_session)]) -> dict[str, str]:
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    @app.get("/api/v1/assets")
    def list_assets(
        session: Annotated[Session, Depends(get_session)],
        _: Annotated[Principal, Depends(require_roles("sgif_reader", "sgif_operator", "sgif_admin"))],
    ) -> list[dict[str, Any]]:
        assets = session.scalars(select(Asset).order_by(Asset.asset_id)).all()
        return [
            {
                "asset_id": asset.asset_id,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "zone": asset.zone,
                "criticality": asset.criticality,
                "owner": asset.owner,
            }
            for asset in assets
        ]

    @app.post("/api/v1/assets", status_code=status.HTTP_201_CREATED)
    def create_asset(
        payload: AssetCreate,
        session: Annotated[Session, Depends(get_session)],
        principal: Annotated[Principal, Depends(require_roles("sgif_operator", "sgif_admin"))],
    ) -> dict[str, str]:
        asset = Asset(**payload.model_dump())
        session.add(asset)
        session.add(
            AuditRecord(
                actor_sub=principal.subject,
                action="asset.created",
                details=json.dumps({"asset_id": payload.asset_id}, separators=(",", ":")),
            )
        )
        try:
            session.commit()
        except IntegrityError as error:
            session.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset ID already exists") from error
        return {"asset_id": payload.asset_id}

    @app.get("/api/v1/events")
    def list_events(
        session: Annotated[Session, Depends(get_session)],
        _: Annotated[Principal, Depends(require_roles("sgif_reader", "sgif_operator", "sgif_admin"))],
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
    ) -> list[dict[str, Any]]:
        events = session.scalars(select(Event).order_by(Event.observed_at.desc(), Event.id.desc()).limit(limit)).all()
        return [
            {
                "id": event.id,
                "source": event.source,
                "observed_at": event.observed_at,
                "event_type": event.event_type,
                "severity": event.severity,
                "summary": event.summary,
                "sensor": event.sensor,
                "src_ip": event.src_ip,
                "src_port": event.src_port,
                "dest_ip": event.dest_ip,
                "dest_port": event.dest_port,
                "protocol": event.protocol,
            }
            for event in events
        ]

    @app.post("/api/v1/events/import", status_code=status.HTTP_201_CREATED)
    def import_events(
        payload: EventImport,
        session: Annotated[Session, Depends(get_session)],
        principal: Annotated[Principal, Depends(require_roles("sgif_operator", "sgif_admin"))],
    ) -> dict[str, int]:
        normalized_events: list[dict[str, Any]] = []
        try:
            for event in iter_normalized_events(payload.content.splitlines(), payload.source):
                normalized_events.append(event)
                if len(normalized_events) > MAX_IMPORT_EVENTS:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Import exceeds 1000 events")
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error

        event_hashes = {
            hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            for event in normalized_events
        }
        existing_hashes = set(session.scalars(select(Event.event_hash).where(Event.event_hash.in_(event_hashes))).all()) if event_hashes else set()
        new_events = [
            event
            for event in normalized_events
            if hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            not in existing_hashes
        ]
        unique_new_events: dict[str, dict[str, Any]] = {}
        for event in new_events:
            event_hash = hashlib.sha256(json.dumps(event, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            unique_new_events[event_hash] = event

        for event_hash, event in unique_new_events.items():
            session.add(
                Event(
                    event_hash=event_hash,
                    source=event["source"],
                    observed_at=event["observed_at"],
                    event_type=event["event_type"],
                    severity=event["severity"],
                    summary=event["summary"],
                    sensor=event["sensor"],
                    src_ip=event["src_ip"],
                    src_port=event["src_port"],
                    dest_ip=event["dest_ip"],
                    dest_port=event["dest_port"],
                    protocol=event["protocol"],
                )
            )
        session.add(
            AuditRecord(
                actor_sub=principal.subject,
                action="events.imported",
                details=json.dumps(
                    {"source": payload.source, "accepted": len(unique_new_events)},
                    separators=(",", ":"),
                ),
            )
        )
        session.commit()
        return {"accepted": len(unique_new_events), "duplicates": len(normalized_events) - len(unique_new_events)}

    return app


app = create_app()