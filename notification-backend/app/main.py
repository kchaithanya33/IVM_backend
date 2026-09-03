from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import deployment

from app.api.notification_arm_api import (
    router as notification_arm_router,
)

from app.api.workflow import (
    router as workflow_router,
)

from app.api.configuration import (
    router as configuration_router,
)

from app.api.key_vault import (
    router as key_vault_router,
)

from app.api.connections import (
    router as connections_router,
)

from app.api.scoping import (
    router as scoping_router,
)

# NEW: AuthScan
from app.api.auth import (
    router as auth_router,
)


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Notification Backend",
    description=(
        "Notification Infrastructure "
        "Deployment API"
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROUTERS
# ============================================================

# ------------------------------------------------------------
# Workflow
# ------------------------------------------------------------

app.include_router(
    workflow_router
)


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

app.include_router(
    configuration_router
)


# ------------------------------------------------------------
# Key Vault
# ------------------------------------------------------------

app.include_router(
    key_vault_router
)


# ------------------------------------------------------------
# Azure API Connections
# ------------------------------------------------------------

app.include_router(
    connections_router
)


# ------------------------------------------------------------
# Function App Deployment
# ------------------------------------------------------------

app.include_router(
    deployment.router
)


# ------------------------------------------------------------
# Notification ARM Deployment
# ------------------------------------------------------------

app.include_router(
    notification_arm_router
)


# ------------------------------------------------------------
# Scoping-00 Logic App Deployment
# ------------------------------------------------------------

app.include_router(
    scoping_router
)


# ------------------------------------------------------------
# AuthScan Logic App Deployment
# ------------------------------------------------------------

app.include_router(
    auth_router
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "status": "running",
        "service": "notification-backend",
    }