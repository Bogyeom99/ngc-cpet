from __future__ import annotations

from typing import Any

import streamlit as st
from supabase import Client, create_client


def is_configured() -> bool:
    return (
        "SUPABASE_URL" in st.secrets
        and "SUPABASE_SERVICE_ROLE_KEY" in st.secrets
        and bool(st.secrets["SUPABASE_URL"])
        and bool(st.secrets["SUPABASE_SERVICE_ROLE_KEY"])
    )


@st.cache_resource
def _client() -> Client:
    if not is_configured():
        raise RuntimeError("Supabase 연결 정보가 설정되지 않았습니다.")
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )


def list_athletes() -> list[dict[str, Any]]:
    if not is_configured():
        return []

    response = (
        _client()
        .table("athletes")
        .select("id,name,sex,category,created_at")
        .order("created_at")
        .execute()
    )
    return list(response.data or [])


def add_athlete(name: str, sex: str, category: str) -> dict[str, Any]:
    if not is_configured():
        raise RuntimeError("Supabase 연결 정보가 설정되지 않았습니다.")

    payload = {
        "name": name.strip(),
        "sex": sex,
        "category": category,
    }

    response = (
        _client()
        .table("athletes")
        .insert(payload)
        .execute()
    )

    if not response.data:
        raise RuntimeError("선수 정보를 저장하지 못했습니다.")

    return dict(response.data[0])
