"""
FM_REA_HeadCoach FastAPI Server & Real-Time WebSocket Engine
Runs the 4-stage tactical analysis pipeline on every tick and streams results to the dashboard.
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.engine.effective_stats import apply_effective_stats_to_team
from app.engine.matchup_matrix import compute_matchup_matrix
from app.engine.rule_engine import TacticalRuleEngine
from app.engine.spatial_analyzer import analyze_spatial_vulnerability
from app.memory.reader import FMMemoryReader
from app.memory.simulator import LiveMatchSimulator
from app.models.match_state import FullAnalysisResponse, MatchSnapshot

app = FastAPI(
    title="FM_REA_HeadCoach API",
    description="Football Manager Real-Time Tactical Vulnerability & Matchup Bleed-Point Engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

simulator = LiveMatchSimulator()
memory_reader = FMMemoryReader(simulator=simulator)
rule_engine = TacticalRuleEngine()


def run_full_analysis(snapshot: MatchSnapshot) -> FullAnalysisResponse:
    """Executes the 4 core mathematical modules on a MatchSnapshot."""
    # Module 1: Effective Stats (Stamina Decay & Yellow Card Penalty)
    apply_effective_stats_to_team(snapshot.my_team)
    apply_effective_stats_to_team(snapshot.opponent_team)

    # Module 2: Spatial Vulnerability Analysis (6 Pitch Zones)
    zones = analyze_spatial_vulnerability(snapshot.my_team, snapshot.opponent_team)
    primary_zone = max(zones, key=lambda z: z.svs_score)

    # Module 3: 1v1 Matchup Bleed-Point Matrix
    matchups, bleed_alerts = compute_matchup_matrix(snapshot.my_team, snapshot.opponent_team)

    # Module 4: Rule-Based Tactical Instruction Generator
    recommendations = rule_engine.evaluate_rules(snapshot, zones, matchups)

    return FullAnalysisResponse(
        snapshot=snapshot,
        zones=zones,
        primary_target_zone=primary_zone,
        matchups=matchups,
        bleed_alerts=bleed_alerts,
        recommendations=recommendations,
    )


class OverridePayload(BaseModel):
    match_minute: Optional[int] = None
    opp_defensive_line: Optional[int] = None
    opp_defensive_width: Optional[int] = None
    opp_dl_condition: Optional[float] = None
    opp_dl_booked: Optional[bool] = None


@app.get("/api/analysis", response_model=FullAnalysisResponse)
def get_current_analysis() -> FullAnalysisResponse:
    snap = memory_reader.read_snapshot()
    return run_full_analysis(snap)


@app.post("/api/scenario/{scenario_id}", response_model=FullAnalysisResponse)
def switch_scenario(scenario_id: str) -> FullAnalysisResponse:
    snap = simulator.load_scenario(scenario_id)
    return run_full_analysis(snap)


@app.post("/api/override", response_model=FullAnalysisResponse)
def override_parameters(payload: OverridePayload) -> FullAnalysisResponse:
    snap = simulator.apply_override(
        match_minute=payload.match_minute,
        opp_defensive_line=payload.opp_defensive_line,
        opp_defensive_width=payload.opp_defensive_width,
        opp_dl_condition=payload.opp_dl_condition,
        opp_dl_booked=payload.opp_dl_booked,
    )
    return run_full_analysis(snap)


@app.websocket("/ws/match")
async def match_websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            snap = memory_reader.read_snapshot()
            analysis = run_full_analysis(snap)
            await websocket.send_json(analysis.model_dump())
            await asyncio.sleep(0.8)
    except WebSocketDisconnect:
        pass


FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/")
def serve_dashboard():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "FM_REA_HeadCoach Backend Running. Open /docs for API."}

