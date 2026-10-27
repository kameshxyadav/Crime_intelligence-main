"""
Authentication and Role Management Router
==========================================
Provides role-based login and session tokens for:
- Station Officer (Field OS)
- Crime Analyst (Analyst OS)
- Police Chief / Admin (Command OS)
- Public Citizen
"""

from __future__ import annotations

import uuid
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/auth", tags=["Authentication & Roles"])


class UserProfile(BaseModel):
    user_id: str
    name: str
    role: str   # "officer" | "analyst" | "admin" | "public"
    badge_number: Optional[str] = None
    station: Optional[str] = None
    jurisdiction: str
    email: str
    token: str


DEMO_USERS = {
    "officer": UserProfile(
        user_id="usr_sec17_officer",
        name="Insp. Rajesh Sharma",
        role="officer",
        badge_number="CHD-POL-1704",
        station="PS-SEC17",
        jurisdiction="Chandigarh Police - Sector 17 Central",
        email="rajesh.sharma@chandigarhpolice.gov.in",
        token="demo_token_officer_sec17",
    ),
    "analyst": UserProfile(
        user_id="usr_cid_analyst",
        name="Dr. Neha Verma",
        role="analyst",
        badge_number="CID-INTEL-882",
        station="CENTRAL_CID",
        jurisdiction="Chandigarh Crime Investigation Wing",
        email="neha.verma@cid.chd.gov.in",
        token="demo_token_analyst_cid",
    ),
    "admin": UserProfile(
        user_id="usr_ssp_admin",
        name="SSP Kanwardeep Kaur, IPS",
        role="admin",
        badge_number="IPS-CHD-001",
        station="POLICE_HQ",
        jurisdiction="Chandigarh Police Headquarters (Sector 9)",
        email="ssp.chandigarh@nic.in",
        token="demo_token_admin_ssp",
    ),
    "public": UserProfile(
        user_id="usr_citizen_anon",
        name="Anonymous Citizen",
        role="public",
        badge_number=None,
        station=None,
        jurisdiction="Public Witness Portal",
        email="anonymous@citizen.portal",
        token="demo_token_citizen",
    ),
}


class LoginRequest(BaseModel):
    role: str
    password: Optional[str] = None


@router.post("/login", response_model=UserProfile)
async def login_user(req: LoginRequest) -> UserProfile:
    role_key = req.role.lower().strip()
    if role_key in DEMO_USERS:
        return DEMO_USERS[role_key]
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Unknown role '{req.role}'. Valid demo roles: officer, analyst, admin, public.",
    )


@router.get("/me", response_model=UserProfile)
async def get_current_user(role: Optional[str] = "officer") -> UserProfile:
    return DEMO_USERS.get(role.lower(), DEMO_USERS["officer"])


@router.get("/users", response_model=List[UserProfile])
async def list_demo_users() -> List[UserProfile]:
    return list(DEMO_USERS.values())
