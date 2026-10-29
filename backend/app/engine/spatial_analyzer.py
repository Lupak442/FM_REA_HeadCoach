"""
Module 2: Spatial Vulnerability Analyzer (상대 수비 블록 및 공백 분석 모듈)
Computes the Space Vulnerability Score (SVS, 0~100) across 6 tactical zones
by comparing effective velocity, off-the-ball movement vs positioning, and agility/turning
between our attackers and opponent defenders, scaled by opponent tactical line/width settings.
"""
from __future__ import annotations
from typing import Dict, List, Sequence
from app.models.match_state import (
    PlayerAttributes,
    PlayerState,
    TeamTacticalState,
    ZoneVulnerability,
)


def _select_players_by_slots(players: Sequence[PlayerState], slots: Sequence[str], fallback_slots: Sequence[str]) -> List[PlayerState]:
    matched = [p for p in players if p.slot in slots]
    if not matched:
        matched = [p for p in players if p.slot in fallback_slots]
    if not matched and players:
        matched = list(players[-2:])
    return matched


def _avg_eff(players: Sequence[PlayerState], attr_name: str) -> float:
    if not players:
        return 12.0
    vals = []
    for p in players:
        eff: PlayerAttributes = p.effective_attrs or p.base_attrs
        vals.append(getattr(eff, attr_name))
    return sum(vals) / len(vals)


def _compute_zone_metrics(
    attackers: Sequence[PlayerState],
    defenders: Sequence[PlayerState],
    tactical_mult: float,
    structural_bonus: float = 0.0,
) -> tuple[float, float, float, float]:
    """
    Returns (svs_score, delta_v, delta_m, delta_a)
    """
    # 1. Velocity Gap (Delta V): 0.55 * Acc + 0.45 * Pace
    att_v = 0.55 * _avg_eff(attackers, "acceleration") + 0.45 * _avg_eff(attackers, "pace")
    def_v = 0.55 * _avg_eff(defenders, "acceleration") + 0.45 * _avg_eff(defenders, "pace")
    delta_v = round(att_v - def_v, 2)

    # 2. Movement vs Positioning Gap (Delta M): (0.60*OtB + 0.40*Ant) - (0.50*Pos + 0.30*Cnt + 0.20*Dec)
    att_m = 0.60 * _avg_eff(attackers, "off_the_ball") + 0.40 * _avg_eff(attackers, "anticipation")
    def_m = (
        0.50 * _avg_eff(defenders, "positioning")
        + 0.30 * _avg_eff(defenders, "concentration")
        + 0.20 * _avg_eff(defenders, "decisions")
    )
    delta_m = round(att_m - def_m, 2)

    # 3. Agility / Turn Responsiveness Gap (Delta A): (0.60*Agi + 0.40*Bal) - (0.65*Agi + 0.35*Bal)
    att_a = 0.60 * _avg_eff(attackers, "agility") + 0.40 * _avg_eff(attackers, "balance")
    def_a = 0.65 * _avg_eff(defenders, "agility") + 0.35 * _avg_eff(defenders, "balance")
    delta_a = round(att_a - def_a, 2)

    z_raw = (0.45 * delta_v + 0.35 * delta_m + 0.20 * delta_a + structural_bonus) * tactical_mult
    svs = max(0.0, min(100.0, round(50.0 + 4.5 * z_raw, 1)))
    return svs, delta_v, delta_m, delta_a


def _classify_status(svs: float) -> str:
    if svs >= 70.0:
        return "CRITICAL_TARGET"
    elif svs >= 58.0:
        return "ADVANTAGE"
    elif svs >= 42.0:
        return "NEUTRAL"
    return "AVOID"


def analyze_spatial_vulnerability(
    my_team: TeamTacticalState,
    opp_team: TeamTacticalState,
) -> List[ZoneVulnerability]:
    """
    Evaluates all 6 pitch zones and returns their Spatial Vulnerability Scores (SVS).
    Note: Attacking Left Flank confronts Opponent's Right Defense (DR/WBR/DC_R).
          Attacking Right Flank confronts Opponent's Left Defense (DL/WBL/DC_L).
    """
    my_p = my_team.players
    opp_p = opp_team.players

    # Check if opponent uses narrow congestion (3 CBs or 2+ DMs or narrow width <= 2)
    opp_cb_count = sum(1 for p in opp_p if p.slot in ("DC_L", "DC_C", "DC_R"))
    opp_dm_count = sum(1 for p in opp_p if p.slot in ("DM_L", "DM_C", "DM_R"))
    has_wide_fullbacks = any(p.slot in ("DL", "DR") for p in opp_p)

    # Tactical Multipliers
    # Narrow defensive width (1 or 2) opens up the flanks (+multiplier on flanks, -multiplier in center)
    flank_mult = round(1.0 + (3 - opp_team.defensive_width) * 0.12 + (0.10 if not has_wide_fullbacks else 0.0), 2)
    halfspace_mult = round(1.0 + (opp_team.pressing_intensity - 3) * 0.08, 2)
    center_mult = round(1.0 - (0.12 if (opp_cb_count >= 3 or opp_dm_count >= 2) else 0.0) + (opp_team.defensive_width - 3) * 0.10, 2)
    behind_mult = round(0.70 + 0.15 * opp_team.defensive_line, 2)

    zones_config = [
        {
            "zone_id": "left_flank",
            "zone_name_kr": "좌측 측면 ( vs 상대 우측 수비 )",
            "att_slots": ("AML", "ML", "DL", "WBL"),
            "att_fallback": ("ST_L", "ST_C", "MC_L"),
            "def_slots": ("DR", "WBR", "MR"),
            "def_fallback": ("DC_R", "DC_C"),
            "mult": flank_mult,
            "bonus": 0.8 if not any(p.slot == "DR" for p in opp_p) else 0.0,
        },
        {
            "zone_id": "right_flank",
            "zone_name_kr": "우측 측면 ( vs 상대 좌측 수비 )",
            "att_slots": ("AMR", "MR", "DR", "WBR"),
            "att_fallback": ("ST_R", "ST_C", "MC_R"),
            "def_slots": ("DL", "WBL", "ML"),
            "def_fallback": ("DC_L", "DC_C"),
            "mult": flank_mult,
            "bonus": 0.8 if not any(p.slot == "DL" for p in opp_p) else 0.0,
        },
        {
            "zone_id": "left_halfspace",
            "zone_name_kr": "좌측 하프스페이스 (채널 침투)",
            "att_slots": ("AML", "AMC", "MC_L", "ST_L"),
            "att_fallback": ("ST_C", "ML"),
            "def_slots": ("DC_R", "DR", "DM_R", "DM_C"),
            "def_fallback": ("DC_C", "MC_R"),
            "mult": halfspace_mult,
            "bonus": 0.0,
        },
        {
            "zone_id": "right_halfspace",
            "zone_name_kr": "우측 하프스페이스 (채널 침투)",
            "att_slots": ("AMR", "AMC", "MC_R", "ST_R"),
            "att_fallback": ("ST_C", "MR"),
            "def_slots": ("DC_L", "DL", "DM_L", "DM_C"),
            "def_fallback": ("DC_C", "MC_L"),
            "mult": halfspace_mult,
            "bonus": 0.0,
        },
        {
            "zone_id": "center_zone14",
            "zone_name_kr": "중앙 2선 (Zone 14 / 아크 정면)",
            "att_slots": ("AMC", "MC_L", "MC_C", "MC_R", "ST_C"),
            "att_fallback": ("AML", "AMR"),
            "def_slots": ("DM_L", "DM_C", "DM_R", "DC_C", "MC_C"),
            "def_fallback": ("DC_L", "DC_R"),
            "mult": center_mult,
            "bonus": -1.2 if (opp_cb_count >= 3 and opp_dm_count >= 1) else (-0.7 if opp_dm_count >= 2 else 0.0),
        },
        {
            "zone_id": "behind_line",
            "zone_name_kr": "수비 라인 뒷공간 (스루패스/침투)",
            "att_slots": ("ST_L", "ST_C", "ST_R", "AML", "AMR"),
            "att_fallback": ("AMC",),
            "def_slots": ("DC_L", "DC_C", "DC_R", "DL", "DR"),
            "def_fallback": ("DM_C",),
            "mult": behind_mult,
            "bonus": (opp_team.defensive_line - 3) * 0.65,
        },
    ]

    results: List[ZoneVulnerability] = []
    for cfg in zones_config:
        atts = _select_players_by_slots(my_p, cfg["att_slots"], cfg["att_fallback"])
        defs = _select_players_by_slots(opp_p, cfg["def_slots"], cfg["def_fallback"])
        svs, dv, dm, da = _compute_zone_metrics(atts, defs, cfg["mult"], cfg["bonus"])
        status = _classify_status(svs)

        if status == "CRITICAL_TARGET":
            summary = f"핵심 공략처! 속도 우위({dv:+.1f}) 및 역동작 격차({da:+.1f})가 매우 큽니다."
        elif status == "ADVANTAGE":
            summary = f"공략 유리 (침투 우위 {dm:+.1f}, 전술 배율 x{cfg['mult']:.2f})"
        elif status == "NEUTRAL":
            summary = f"공수 균형 구역 (SVS {svs:.1f})"
        else:
            summary = f"밀집/열세 구역 - 우회 권장 (SVS {svs:.1f})"

        results.append(
            ZoneVulnerability(
                zone_id=cfg["zone_id"],
                zone_name_kr=cfg["zone_name_kr"],
                svs_score=svs,
                velocity_gap=dv,
                movement_gap=dm,
                agility_gap=da,
                tactical_multiplier=cfg["mult"],
                status_label=status,  # type: ignore[arg-type]
                summary=summary,
            )
        )

    return results

