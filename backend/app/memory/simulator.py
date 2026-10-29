"""
Real-Time Match Simulator (가상 경기 및 시나리오 시뮬레이터)
Provides 3 realistic tactical scenarios and dynamic live match progression
(stamina drain, tactical shifts, yellow card events) so the system can be tested
and calibrated even when fm.exe is not running.
"""
from __future__ import annotations
import copy
from typing import Dict
from app.models.match_state import (
    MatchSnapshot,
    PlayerAttributes,
    PlayerState,
    TeamTacticalState,
)


def _make_attrs(**overrides: float) -> PlayerAttributes:
    defaults = dict(
        pace=13.0, acceleration=13.0, agility=13.0, balance=13.0,
        jumping_reach=12.0, strength=12.0, stamina=14.0,
        dribbling=12.0, first_touch=13.0, passing=13.0, crossing=12.0,
        tackling=12.0, marking=12.0, heading=12.0, flair=12.0,
        off_the_ball=13.0, positioning=12.0, anticipation=13.0,
        decisions=13.0, composure=13.0, concentration=12.0,
        aggression=13.0, bravery=13.0,
    )
    defaults.update(overrides)
    return PlayerAttributes(**defaults)


def _build_my_default_team() -> TeamTacticalState:
    return TeamTacticalState(
        team_name="FC 서울 헤드코치 (우리 팀)",
        formation="4-2-3-1 Wide",
        mentality=4,
        defensive_line=4,
        pressing_intensity=4,
        defensive_width=3,
        players=[
            PlayerState(
                player_id=101,
                name="이강인 (AMR)",
                shirt_number=19,
                slot="AMR",
                role_name="인버티드 윙어 (공격)",
                condition=86.0,
                is_booked=False,
                match_rating=7.4,
                base_attrs=_make_attrs(
                    pace=15, acceleration=16, agility=18, balance=17,
                    dribbling=18, flair=18, first_touch=17, passing=17, crossing=16,
                    off_the_ball=16, anticipation=16, decisions=15, jumping_reach=8, heading=8
                ),
            ),
            PlayerState(
                player_id=102,
                name="손흥민 (AML)",
                shirt_number=7,
                slot="AML",
                role_name="인사이드 포워드 (공격)",
                condition=84.0,
                is_booked=False,
                match_rating=7.5,
                base_attrs=_make_attrs(
                    pace=17, acceleration=17, agility=16, balance=15,
                    dribbling=16, flair=16, first_touch=16, off_the_ball=18,
                    anticipation=17, composure=17, jumping_reach=12, heading=12
                ),
            ),
            PlayerState(
                player_id=103,
                name="오현규 (ST)",
                shirt_number=9,
                slot="ST_C",
                role_name="전진형 포워드 (공격)",
                condition=85.0,
                is_booked=False,
                match_rating=7.1,
                base_attrs=_make_attrs(
                    pace=15, acceleration=16, agility=15, balance=16,
                    jumping_reach=14, strength=16, heading=14, bravery=16,
                    dribbling=14, off_the_ball=16, anticipation=15
                ),
            ),
            PlayerState(
                player_id=104,
                name="이재성 (AMC)",
                shirt_number=10,
                slot="AMC",
                role_name="공격형 미드필더 (지원)",
                condition=82.0,
                is_booked=False,
                match_rating=7.2,
                base_attrs=_make_attrs(
                    pace=13, acceleration=14, agility=15, balance=15,
                    passing=15, first_touch=16, off_the_ball=17, anticipation=17,
                    decisions=16, stamina=18, tackling=12
                ),
            ),
        ],
    )


SCENARIOS: Dict[str, MatchSnapshot] = {
    # 시나리오 1: 상대 좌측 풀백 체력 고갈(64%) + 경고 1장 & 높은 수비 라인 + 둔한 센터백
    "high_line_tired_fb": MatchSnapshot(
        match_minute=68,
        home_score=1,
        away_score=1,
        data_source="SIMULATOR",
        scenario_id="high_line_tired_fb",
        my_team=_build_my_default_team(),
        opponent_team=TeamTacticalState(
            team_name="레알 마드리드 B (상대 팀)",
            formation="4-3-3 High Press",
            mentality=4,
            defensive_line=5,        # 매우 높은 수비 라인 -> 뒷공간 노출
            pressing_intensity=4,
            defensive_width=2,       # 좁은 수비 폭 -> 측면 노출
            players=[
                PlayerState(
                    player_id=201,
                    name="M. 구티에레스 (DL)",
                    shirt_number=3,
                    slot="DL",
                    role_name="완성형 윙백 (공격)",
                    condition=64.0,  # 체력 70% 이하로 급락!
                    is_booked=True,  # 옐로카드 1장 보유!
                    match_rating=6.2,
                    base_attrs=_make_attrs(
                        pace=14, acceleration=14, agility=13, balance=12,
                        tackling=11, marking=10, positioning=10, concentration=10,
                        jumping_reach=10, heading=9, composure=13, first_touch=14
                    ),
                ),
                PlayerState(
                    player_id=202,
                    name="D. 카르바할 (DR)",
                    shirt_number=2,
                    slot="DR",
                    role_name="풀백 (지원)",
                    condition=78.0,
                    is_booked=False,
                    match_rating=6.9,
                    base_attrs=_make_attrs(
                        pace=14, acceleration=14, agility=14, balance=15,
                        tackling=15, marking=14, positioning=15, concentration=15,
                        jumping_reach=11, heading=12, composure=15
                    ),
                ),
                PlayerState(
                    player_id=203,
                    name="N. 코바치 (DC_L)",
                    shirt_number=4,
                    slot="DC_L",
                    role_name="중앙 수비수 (방어)",
                    condition=73.0,
                    is_booked=False,
                    match_rating=6.5,
                    base_attrs=_make_attrs(
                        pace=11, acceleration=10, agility=9, balance=11,  # 발목 회전/역동작 매우 취약, 주력 느림
                        jumping_reach=17, heading=17, strength=17,        # 제공권은 압도적 -> 낮은 크로스 유도!
                        tackling=14, marking=14, positioning=13,
                        composure=9, first_touch=9, decisions=10, passing=10  # 빌드업 압박 구멍!
                    ),
                ),
                PlayerState(
                    player_id=204,
                    name="R. 아센시오 (DC_R)",
                    shirt_number=5,
                    slot="DC_R",
                    role_name="공격형 수비수 (방어)",
                    condition=76.0,
                    is_booked=False,
                    match_rating=6.7,
                    base_attrs=_make_attrs(
                        pace=12, acceleration=11, agility=10, balance=12,
                        jumping_reach=16, heading=16, strength=16,
                        tackling=14, marking=13, positioning=13,
                        composure=12, first_touch=12, decisions=12
                    ),
                ),
                PlayerState(
                    player_id=205,
                    name="M. 마르틴 (DM)",
                    shirt_number=6,
                    slot="DM_C",
                    role_name="볼 위닝 미드필더 (방어)",
                    condition=74.0,
                    is_booked=True,
                    match_rating=6.6,
                    base_attrs=_make_attrs(
                        pace=12, acceleration=12, agility=12,
                        tackling=15, marking=14, positioning=14, aggression=16,
                        composure=11, first_touch=11, decisions=11
                    ),
                ),
            ],
        ),
    ),

    # 시나리오 2: 상대 3-5-2 극단적 중앙 밀집 저블록 (측면 윙백 독박 & 체력 방전)
    "low_block_central_congestion": MatchSnapshot(
        match_minute=74,
        home_score=0,
        away_score=0,
        data_source="SIMULATOR",
        scenario_id="low_block_central_congestion",
        my_team=_build_my_default_team(),
        opponent_team=TeamTacticalState(
            team_name="아틀레티코 마드리드 (상대 팀)",
            formation="5-3-2 Low Block",
            mentality=2,
            defensive_line=2,        # 낮은 수비 라인
            pressing_intensity=2,
            defensive_width=1,       # 극단적 중앙 밀집 -> 측면 광활
            players=[
                PlayerState(
                    player_id=301,
                    name="S. 리노 (WBL)",
                    shirt_number=12,
                    slot="WBL",
                    role_name="윙백 (지원)",
                    condition=61.0,  # 왕복 달리기 후 체력 고갈
                    is_booked=False,
                    match_rating=6.4,
                    base_attrs=_make_attrs(
                        pace=15, acceleration=15, agility=14,
                        tackling=10, marking=9, positioning=9, concentration=9,
                        jumping_reach=9, heading=8
                    ),
                ),
                PlayerState(
                    player_id=302,
                    name="N. 몰리나 (WBR)",
                    shirt_number=16,
                    slot="WBR",
                    role_name="윙백 (지원)",
                    condition=63.0,
                    is_booked=True,
                    match_rating=6.3,
                    base_attrs=_make_attrs(
                        pace=15, acceleration=15, agility=13,
                        tackling=11, marking=10, positioning=10, concentration=10
                    ),
                ),
                PlayerState(
                    player_id=303,
                    name="J. 히메네스 (DC_C)",
                    shirt_number=2,
                    slot="DC_C",
                    role_name="중앙 수비수 (방어)",
                    condition=81.0,
                    is_booked=False,
                    match_rating=7.3,
                    base_attrs=_make_attrs(
                        pace=13, acceleration=12, agility=11,
                        jumping_reach=16, heading=17, strength=17,
                        tackling=16, marking=16, positioning=16, concentration=15
                    ),
                ),
                PlayerState(
                    player_id=304,
                    name="R. 르노르망 (DC_L)",
                    shirt_number=24,
                    slot="DC_L",
                    role_name="중앙 수비수 (방어)",
                    condition=80.0,
                    is_booked=False,
                    match_rating=7.1,
                    base_attrs=_make_attrs(
                        pace=13, acceleration=12, agility=11,
                        jumping_reach=16, heading=16, strength=16,
                        tackling=15, marking=16, positioning=16
                    ),
                ),
                PlayerState(
                    player_id=305,
                    name="A. 비첼 (DC_R)",
                    shirt_number=20,
                    slot="DC_R",
                    role_name="리베로 (지원)",
                    condition=69.0,
                    is_booked=False,
                    match_rating=6.8,
                    base_attrs=_make_attrs(
                        pace=9, acceleration=9, agility=10,
                        jumping_reach=15, heading=14, strength=15,
                        tackling=14, marking=14, positioning=16, composure=16
                    ),
                ),
            ],
        ),
    ),

    # 시나리오 3: 상대 단신 수비진 & 빌드업 미숙 (제공권 폭격 + 전방 압박 트랩)
    "aerial_mismatch_press_trap": MatchSnapshot(
        match_minute=55,
        home_score=2,
        away_score=1,
        data_source="SIMULATOR",
        scenario_id="aerial_mismatch_press_trap",
        my_team=_build_my_default_team(),
        opponent_team=TeamTacticalState(
            team_name="브라이튼 유스 (상대 팀)",
            formation="4-2-3-1 Build-up",
            mentality=4,
            defensive_line=4,
            pressing_intensity=4,
            defensive_width=3,
            players=[
                PlayerState(
                    player_id=401,
                    name="V. 바르코 (DL)",
                    shirt_number=19,
                    slot="DL",
                    role_name="인버티드 윙백",
                    condition=76.0,
                    is_booked=False,
                    match_rating=6.5,
                    base_attrs=_make_attrs(
                        pace=14, acceleration=15, agility=15,
                        jumping_reach=7, heading=7, strength=8,  # 극단적 제공권 약점
                        tackling=11, marking=10, positioning=10
                    ),
                ),
                PlayerState(
                    player_id=402,
                    name="T. 램프티 (DR)",
                    shirt_number=2,
                    slot="DR",
                    role_name="윙백 (공격)",
                    condition=74.0,
                    is_booked=False,
                    match_rating=6.6,
                    base_attrs=_make_attrs(
                        pace=17, acceleration=18, agility=16,
                        jumping_reach=6, heading=6, strength=7,
                        tackling=11, marking=10, positioning=9
                    ),
                ),
                PlayerState(
                    player_id=403,
                    name="I. 마르티네스 (DC_L)",
                    shirt_number=4,
                    slot="DC_L",
                    role_name="공격형 수비수",
                    condition=77.0,
                    is_booked=False,
                    match_rating=6.4,
                    base_attrs=_make_attrs(
                        pace=13, acceleration=13, agility=13,
                        jumping_reach=10, heading=11, strength=11,  # 단신 센터백 -> 높은 크로스 타겟!
                        tackling=13, marking=13, positioning=12,
                        composure=8, first_touch=9, decisions=9, passing=9
                    ),
                ),
                PlayerState(
                    player_id=404,
                    name="J. 폴 헤케 (DC_R)",
                    shirt_number=5,
                    slot="DC_R",
                    role_name="중앙 수비수",
                    condition=79.0,
                    is_booked=False,
                    match_rating=6.5,
                    base_attrs=_make_attrs(
                        pace=12, acceleration=12, agility=12,
                        jumping_reach=11, heading=11, strength=12,
                        tackling=13, marking=13, positioning=12,
                        composure=9, first_touch=10, decisions=10, passing=10
                    ),
                ),
            ],
        ),
    ),
}


class LiveMatchSimulator:
    def __init__(self) -> None:
        self._current_scenario_id: str = "high_line_tired_fb"
        self._state: MatchSnapshot = copy.deepcopy(SCENARIOS[self._current_scenario_id])

    def get_snapshot(self) -> MatchSnapshot:
        return copy.deepcopy(self._state)

    def load_scenario(self, scenario_id: str) -> MatchSnapshot:
        if scenario_id in SCENARIOS:
            self._current_scenario_id = scenario_id
            self._state = copy.deepcopy(SCENARIOS[scenario_id])
        return self.get_snapshot()

    def apply_override(
        self,
        match_minute: int | None = None,
        opp_defensive_line: int | None = None,
        opp_defensive_width: int | None = None,
        opp_dl_condition: float | None = None,
        opp_dl_booked: bool | None = None,
    ) -> MatchSnapshot:
        if match_minute is not None:
            self._state.match_minute = max(1, min(120, match_minute))
        if opp_defensive_line is not None:
            self._state.opponent_team.defensive_line = max(1, min(5, opp_defensive_line))
        if opp_defensive_width is not None:
            self._state.opponent_team.defensive_width = max(1, min(5, opp_defensive_width))

        for p in self._state.opponent_team.players:
            if p.slot in ("DL", "WBL"):
                if opp_dl_condition is not None:
                    p.condition = max(10.0, min(100.0, opp_dl_condition))
                if opp_dl_booked is not None:
                    p.is_booked = opp_dl_booked
        return self.get_snapshot()

