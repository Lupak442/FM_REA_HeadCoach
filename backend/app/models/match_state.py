"""
FM_REA_HeadCoach Data Models & Schemas
Defines player attributes, live match state, tactical configurations, and analysis output structures.
"""
from __future__ import annotations
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class PlayerAttributes(BaseModel):
    """FM 1~20 scale core attributes required for spatial & matchup calculations."""
    # Physical
    pace: float = Field(..., ge=1, le=20, description="주력 (Pace)")
    acceleration: float = Field(..., ge=1, le=20, description="순간속도 (Acceleration)")
    agility: float = Field(..., ge=1, le=20, description="민첩성 (Agility - 발목 회전/역동작 저항)")
    balance: float = Field(..., ge=1, le=20, description="균형감각 (Balance)")
    jumping_reach: float = Field(..., ge=1, le=20, description="점프거리 (Jumping Reach)")
    strength: float = Field(..., ge=1, le=20, description="몸싸움 (Strength)")
    stamina: float = Field(..., ge=1, le=20, description="지구력 (Stamina)")

    # Technical
    dribbling: float = Field(..., ge=1, le=20, description="드리블 (Dribbling)")
    first_touch: float = Field(..., ge=1, le=20, description="퍼스트터치 (First Touch)")
    passing: float = Field(..., ge=1, le=20, description="패스 (Passing)")
    crossing: float = Field(..., ge=1, le=20, description="크로스 (Crossing)")
    tackling: float = Field(..., ge=1, le=20, description="태클 (Tackling)")
    marking: float = Field(..., ge=1, le=20, description="일대일마크 (Marking)")
    heading: float = Field(..., ge=1, le=20, description="헤더 (Heading)")
    flair: float = Field(..., ge=1, le=20, description="개인기 (Flair)")

    # Mental
    off_the_ball: float = Field(..., ge=1, le=20, description="오프더볼 (Off The Ball)")
    positioning: float = Field(..., ge=1, le=20, description="수비 위치선정 (Positioning)")
    anticipation: float = Field(..., ge=1, le=20, description="예측력 (Anticipation)")
    decisions: float = Field(..., ge=1, le=20, description="판단력 (Decisions)")
    composure: float = Field(..., ge=1, le=20, description="침착성 (Composure)")
    concentration: float = Field(..., ge=1, le=20, description="집중력 (Concentration)")
    aggression: float = Field(..., ge=1, le=20, description="적극성 (Aggression)")
    bravery: float = Field(..., ge=1, le=20, description="대담성 (Bravery)")


PositionSlot = Literal[
    "GK",
    "DL", "DC_L", "DC_C", "DC_R", "DR",
    "WBL", "DM_L", "DM_C", "DM_R", "WBR",
    "ML", "MC_L", "MC_C", "MC_R", "MR",
    "AML", "AMC", "AMR",
    "ST_L", "ST_C", "ST_R",
]


class PlayerState(BaseModel):
    """Live player state read from memory or simulator."""
    player_id: int
    name: str
    shirt_number: int
    slot: PositionSlot
    role_name: str = Field(..., description="예: 인버티드 윙어(공), 완성형 윙백(수)")
    condition: float = Field(..., ge=0.0, le=100.0, description="현재 체력 (%)")
    is_booked: bool = Field(default=False, description="옐로카드 보유 여부")
    match_rating: float = Field(default=6.8, ge=1.0, le=10.0, description="실시간 평점")
    base_attrs: PlayerAttributes
    effective_attrs: Optional[PlayerAttributes] = None
    stamina_decay_factor: float = Field(default=1.0, description="체력 감쇠 계수 gamma(C)")


class TeamTacticalState(BaseModel):
    """Team formation and tactical slider settings (1~5 scale)."""
    team_name: str
    formation: str = Field(..., description="예: 4-2-3-1, 3-5-2, 4-3-3")
    mentality: int = Field(..., ge=1, le=5, description="1:매우수비적 ~ 5:매우공격적")
    defensive_line: int = Field(..., ge=1, le=5, description="1:매우낮음 ~ 5:매우높음")
    pressing_intensity: int = Field(..., ge=1, le=5, description="1:거의안함 ~ 5:매우강함")
    defensive_width: int = Field(..., ge=1, le=5, description="1:매우좁게(중앙밀집) ~ 5:매우넓게")
    players: List[PlayerState]


class MatchSnapshot(BaseModel):
    """Complete live match snapshot at a given tick."""
    match_minute: int = Field(..., ge=0, le=120)
    home_score: int = 0
    away_score: int = 0
    data_source: Literal["PYMEM_LIVE", "SIMULATOR"] = "SIMULATOR"
    scenario_id: str = "high_line_tired_fb"
    my_team: TeamTacticalState
    opponent_team: TeamTacticalState


class ZoneVulnerability(BaseModel):
    """Spatial Vulnerability Score (SVS) for a pitch zone."""
    zone_id: Literal[
        "left_flank",
        "left_halfspace",
        "center_zone14",
        "right_halfspace",
        "right_flank",
        "behind_line",
    ]
    zone_name_kr: str
    svs_score: float = Field(..., ge=0.0, le=100.0, description="공간 취약도 점수 (0~100)")
    velocity_gap: float = Field(..., description="속도 우위 격차 (Delta V)")
    movement_gap: float = Field(..., description="오프더볼 vs 위치선정 격차 (Delta M)")
    agility_gap: float = Field(..., description="민첩성/발목 회전 격차 (Delta A)")
    tactical_multiplier: float = Field(..., description="전술 배율 (M_tactic)")
    status_label: Literal["CRITICAL_TARGET", "ADVANTAGE", "NEUTRAL", "AVOID"]
    summary: str


class MatchupPairResult(BaseModel):
    """1v1 matchup bleed-point analysis result."""
    pair_id: str
    zone_label: str
    attacker_name: str
    attacker_slot: str
    attacker_condition: float
    defender_name: str
    defender_slot: str
    defender_condition: float
    defender_booked: bool
    dribble_prob: float = Field(..., description="1:1 온더볼 돌파 기대 확률 (%)")
    aerial_prob: float = Field(..., description="공중볼/파포스트 경합 승률 (%)")
    press_trap_prob: float = Field(..., description="압박 시 턴오버 유발 확률 (%)")
    velocity_diff: float
    agility_diff: float
    is_bleed_point: bool
    bleed_reasons: List[str]


class TacticalRecommendation(BaseModel):
    """Rule Engine output: actionable FM instructions."""
    rule_id: str
    priority: Literal["URGENT", "HIGH", "MEDIUM"]
    category: Literal["TEAM_INSTRUCTION", "PLAYER_INSTRUCTION", "OPPOSITION_INSTRUCTION"]
    title: str
    action_badges: List[str] = Field(..., description="인게임에서 클릭할 지시 버튼명")
    reasoning: str
    trigger_metric: str


class FullAnalysisResponse(BaseModel):
    """Complete payload broadcast to the frontend dashboard."""
    snapshot: MatchSnapshot
    zones: List[ZoneVulnerability]
    primary_target_zone: ZoneVulnerability
    matchups: List[MatchupPairResult]
    bleed_alerts: List[MatchupPairResult]
    recommendations: List[TacticalRecommendation]

