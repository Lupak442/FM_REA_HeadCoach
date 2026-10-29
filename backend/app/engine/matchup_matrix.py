"""
Module 3: Matchup Matrix & Bleed-Point Mapping (매치업 유혈 지점 매핑 모듈)
Computes pairwise 1v1 confrontation probabilities using logistic sigmoid functions:
  - P_dribble: On-the-ball 1v1 breakthrough probability (%)
  - P_aerial: Aerial / Far-post header dominance probability (%)
  - P_press_trap: Pressing turnover induction probability (%)
Detects urgent bleed-points (체력 고갈, 경고 누적, 제공권 미스매치, 빌드업 구멍).
"""
from __future__ import annotations
import math
from typing import List, Optional, Sequence, Tuple
from app.models.match_state import (
    MatchupPairResult,
    PlayerAttributes,
    PlayerState,
    TeamTacticalState,
)


def _sigmoid_pct(x: float, k: float) -> float:
    val = 100.0 / (1.0 + math.exp(-k * x))
    return round(val, 1)


def _find_player(players: Sequence[PlayerState], preferred_slots: Sequence[str]) -> Optional[PlayerState]:
    for slot in preferred_slots:
        for p in players:
            if p.slot == slot:
                return p
    return players[-1] if players else None


def evaluate_1v1_pair(
    pair_id: str,
    zone_label: str,
    att: PlayerState,
    dfn: PlayerState,
) -> MatchupPairResult:
    a: PlayerAttributes = att.effective_attrs or att.base_attrs
    d: PlayerAttributes = dfn.effective_attrs or dfn.base_attrs

    # 1. On-the-ball 1v1 Dribble Breakthrough Probability (P_dribble)
    x_dri = (
        0.35 * a.dribbling + 0.25 * a.acceleration + 0.20 * a.agility + 0.20 * a.flair
    ) - (
        0.35 * d.tackling + 0.25 * d.marking + 0.20 * d.positioning + 0.20 * d.agility
    )
    p_dribble = _sigmoid_pct(x_dri, 0.28)

    # 2. Aerial / Far-post Dominance Probability (P_aerial)
    x_air = (
        0.45 * a.jumping_reach + 0.25 * a.heading + 0.20 * a.strength + 0.10 * a.bravery
    ) - (
        0.45 * d.jumping_reach + 0.25 * d.heading + 0.20 * d.strength + 0.10 * d.bravery
    )
    p_aerial = _sigmoid_pct(x_air, 0.30)

    # 3. Pressing Turnover Induction Probability (P_press_trap)
    x_trap = 13.0 - (
        0.30 * d.composure + 0.25 * d.first_touch + 0.25 * d.decisions + 0.20 * d.passing
    )
    p_press_trap = _sigmoid_pct(x_trap, 0.35)

    vel_diff = round((0.55 * a.acceleration + 0.45 * a.pace) - (0.55 * d.acceleration + 0.45 * d.pace), 2)
    agi_diff = round((0.60 * a.agility + 0.40 * a.balance) - (0.65 * d.agility + 0.35 * d.balance), 2)

    # Bleed-Point Trigger Evaluation
    bleed_reasons: List[str] = []

    # Trigger A: Defender Stamina Depletion + High Breakthrough
    if dfn.condition <= 70.0 and p_dribble >= 66.0:
        bleed_reasons.append(
            f"[체력 고갈 유혈지점] {dfn.name} 체력 {dfn.condition:.0f}% 저하 → {att.name} 1:1 돌파 성공 기대치 {p_dribble:.1f}%"
        )
    elif p_dribble >= 72.0:
        bleed_reasons.append(
            f"[1:1 기술/주력 압도] {att.name} vs {dfn.name} 온더볼 돌파 우위 ({p_dribble:.1f}%)"
        )

    # Trigger B: Yellow Card Caution Target
    if dfn.is_booked and p_dribble >= 60.0:
        bleed_reasons.append(
            f"[경고 누적 타겟] {dfn.name} 옐로카드 보유(태클/적극성 -15% 페널티) → 돌파/파울 유도 확률 {p_dribble:.1f}%"
        )

    # Trigger C: Aerial / Far-post Mismatch
    if p_aerial >= 71.0:
        bleed_reasons.append(
            f"[제공권/파포스트 미스매치] {att.name} 공중볼 경합 승률 {p_aerial:.1f}% (높은 크로스 타겟)"
        )

    # Trigger D: Pressing Trap Target
    if p_press_trap >= 68.0:
        bleed_reasons.append(
            f"[빌드업 압박 함정] {dfn.name} 압박 저항력 취약(침착 {dfn.base_attrs.composure:.0f}/터치 {dfn.base_attrs.first_touch:.0f}) → 턴오버 유발 {p_press_trap:.1f}%"
        )

    return MatchupPairResult(
        pair_id=pair_id,
        zone_label=zone_label,
        attacker_name=att.name,
        attacker_slot=att.slot,
        attacker_condition=round(att.condition, 1),
        defender_name=dfn.name,
        defender_slot=dfn.slot,
        defender_condition=round(dfn.condition, 1),
        defender_booked=dfn.is_booked,
        dribble_prob=p_dribble,
        aerial_prob=p_aerial,
        press_trap_prob=p_press_trap,
        velocity_diff=vel_diff,
        agility_diff=agi_diff,
        is_bleed_point=len(bleed_reasons) > 0,
        bleed_reasons=bleed_reasons,
    )


def compute_matchup_matrix(
    my_team: TeamTacticalState,
    opp_team: TeamTacticalState,
) -> Tuple[List[MatchupPairResult], List[MatchupPairResult]]:
    """
    Builds key positional 1v1 confrontation pairs and extracts urgent bleed-point alerts.
    """
    pair_definitions = [
        ("right_wing_1v1", "우측 윙어 vs 상대 좌측 풀백", ("AMR", "MR", "ST_R", "WBR"), ("DL", "WBL", "DC_L")),
        ("left_wing_1v1", "좌측 윙어 vs 상대 우측 풀백", ("AML", "ML", "ST_L", "WBL"), ("DR", "WBR", "DC_R")),
        ("striker_vs_lcb", "중앙 스트라이커 vs 상대 좌측 센터백", ("ST_C", "ST_R", "AMC"), ("DC_L", "DC_C")),
        ("striker_vs_rcb", "중앙 스트라이커 vs 상대 우측 센터백", ("ST_C", "ST_L", "AMC"), ("DC_R", "DC_C")),
        ("amc_vs_dm", "공격형 미드필더 vs 상대 수비형 미드필더", ("AMC", "MC_C", "MC_L"), ("DM_C", "DM_L", "MC_C", "DC_C")),
    ]

    matchups: List[MatchupPairResult] = []
    for pair_id, label, att_slots, def_slots in pair_definitions:
        att = _find_player(my_team.players, att_slots)
        dfn = _find_player(opp_team.players, def_slots)
        if att and dfn:
            res = evaluate_1v1_pair(pair_id, label, att, dfn)
            matchups.append(res)

    bleed_alerts = [m for m in matchups if m.is_bleed_point]
    bleed_alerts.sort(
        key=lambda m: max(m.dribble_prob, m.aerial_prob, m.press_trap_prob),
        reverse=True,
    )
    return matchups, bleed_alerts

