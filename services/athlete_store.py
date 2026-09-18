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


def list_measurements(athlete_id: int) -> list[dict[str, Any]]:
    if not is_configured():
        return []

    response = (
        _client()
        .table("athlete_measurements")
        .select(
            "id,athlete_id,test_date,height,weight,bmi,vo2max,hrmax,"
            "exercise_time,load_type,max_load,grade_percent,created_at,updated_at"
        )
        .eq("athlete_id", athlete_id)
        .order("test_date", desc=True)
        .execute()
    )
    return list(response.data or [])


def save_measurement(
    athlete_id: int,
    test_date: str,
    height: float,
    weight: float,
    bmi: float,
    vo2max: float,
    hrmax: int,
    exercise_time: str,
    load_type: str,
    max_load: float,
    grade_percent: float,
) -> dict[str, Any]:
    if not is_configured():
        raise RuntimeError("Supabase 연결 정보가 설정되지 않았습니다.")

    payload = {
        "athlete_id": athlete_id,
        "test_date": test_date,
        "height": height,
        "weight": weight,
        "bmi": bmi,
        "vo2max": vo2max,
        "hrmax": hrmax,
        "exercise_time": exercise_time,
        "load_type": load_type,
        "max_load": max_load,
        "grade_percent": grade_percent,
    }

    response = (
        _client()
        .table("athlete_measurements")
        .upsert(
            payload,
            on_conflict="athlete_id,test_date",
        )
        .execute()
    )

    if not response.data:
        raise RuntimeError("측정 정보를 저장하지 못했습니다.")

    return dict(response.data[0])
