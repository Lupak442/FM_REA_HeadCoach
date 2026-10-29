"""
Module 4: Tactical Instruction Guideline Generator (전술 지시 가이드라인 자동 생성 규칙 엔진)
Translates Spatial Vulnerability Scores (SVS) and Matchup Bleed Matrix into concrete,
clickable Football Manager Team Instructions (TI), Player Instructions (PI), and Opposition Instructions (OI).
Includes Hysteresis memory to prevent UI flickering when live stats oscillate near thresholds.
"""
from __future__ import annotations
from typing import Dict, List
from app.models.match_state import (
    MatchSnapshot,
    MatchupPairResult,
    TacticalRecommendation,
    ZoneVulnerability,
)


class TacticalRuleEngine:
    def __init__(self) -> None:
        # Hysteresis memory: rule_id -> last_triggered_match_minute
        self._active_rules_since: Dict[str, int] = {}
        self._cooldown_minutes: int = 3

    def _is_active_with_hysteresis(
        self,
        rule_id: str,
        current_minute: int,
        trigger_val: float,
        on_threshold: float,
        off_threshold: float,
    ) -> bool:
        was_active = rule_id in self._active_rules_since
        if not was_active:
            if trigger_val >= on_threshold:
                self._active_rules_since[rule_id] = current_minute
                return True
            return False
        else:
            last_min = self._active_rules_since[rule_id]
            # Keep active for at least _cooldown_minutes or until value drops below off_threshold
            if (current_minute - last_min) < self._cooldown_minutes or trigger_val >= off_threshold:
                return True
            del self._active_rules_since[rule_id]
            return False

    def evaluate_rules(
        self,
        snapshot: MatchSnapshot,
        zones: List[ZoneVulnerability],
        matchups: List[MatchupPairResult],
    ) -> List[TacticalRecommendation]:
        recs: List[TacticalRecommendation] = []
        zone_map = {z.zone_id: z for z in zones}
        minute = snapshot.match_minute
        opp = snapshot.opponent_team

        left_flank = zone_map["left_flank"]
        right_flank = zone_map["right_flank"]
        center_z14 = zone_map["center_zone14"]
        behind_line = zone_map["behind_line"]

        # Check central congestion
        opp_cb_count = sum(1 for p in opp.players if p.slot in ("DC_L", "DC_C", "DC_R"))
        opp_dm_count = sum(1 for p in opp.players if p.slot in ("DM_L", "DM_C", "DM_R"))
        is_central_congested = opp.defensive_width <= 2 or opp_cb_count >= 3 or opp_dm_count >= 2 or center_z14.svs_score <= 45.0

        # ---------------------------------------------------------------------
        # R-01: 상대 중앙 밀집 수비 블록 우회 & 측면 집중 공략
        # ---------------------------------------------------------------------
        best_flank = right_flank if right_flank.svs_score >= left_flank.svs_score else left_flank
        flank_dir = "우측 측면" if best_flank.zone_id == "right_flank" else "좌측 측면"
        if is_central_congested and self._is_active_with_hysteresis(
            "R-01", minute, best_flank.svs_score, on_threshold=64.0, off_threshold=61.0
        ):
            recs.append(
                TacticalRecommendation(
                    rule_id="R-01",
                    priority="URGENT" if best_flank.svs_score >= 72.0 else "HIGH",
                    category="TEAM_INSTRUCTION",
                    title=f"중앙 밀집 블록 우회 → [{flank_dir} 집중 공략] 및 패스 길이 조정",
                    action_badges=[
                        "패스 길이: 짧게 → 혼합",
                        "공격 폭: 넓게",
                        f"{flank_dir} 집중 공략",
                    ],
                    reasoning=(
                        f"상대가 중앙 밀집형 수비(포메이션 {opp.formation}, 중앙 SVS {center_z14.svs_score:.1f})를 사용 중입니다. "
                        f"패스 길이를 '짧게'에서 '혼합'으로 바꾸고, 공백이 가장 큰 {flank_dir}(SVS {best_flank.svs_score:.1f}) 공략을 지시하세요."
                    ),
                    trigger_metric=f"{flank_dir} SVS {best_flank.svs_score:.1f} vs 중앙 {center_z14.svs_score:.1f}",
                )
            )

        # ---------------------------------------------------------------------
        # R-02: 높은 수비 라인 & 센터백 발목 회전/주력 열세 → 뒷공간 스루패스 폭격
        # ---------------------------------------------------------------------
        if opp.defensive_line >= 4 and self._is_active_with_hysteresis(
            "R-02", minute, behind_line.svs_score, on_threshold=68.0, off_threshold=65.0
        ):
            recs.append(
                TacticalRecommendation(
                    rule_id="R-02",
                    priority="URGENT",
                    category="TEAM_INSTRUCTION",
                    title="상대 높은 수비라인 뒷공간 균열 → [공간으로 패스하라] 즉시 활성화",
                    action_badges=[
                        "공간으로 패스하라 (Pass Into Space)",
                        "템포: 빠르게",
                        "공격수: 라인 침투 / 위험 감수 패스",
                    ],
                    reasoning=(
                        f"상대 수비 라인이 높고(단계 {opp.defensive_line}/5), 우리 공격진의 주력 우위(ΔV {behind_line.velocity_gap:+.1f}) 및 "
                        f"수비수 발목 회전 역동작 격차(ΔA {behind_line.agility_gap:+.1f})가 큽니다. 뒷공간 침투 패스로 일대일 찬스를 만드세요."
                    ),
                    trigger_metric=f"뒷공간 SVS {behind_line.svs_score:.1f} | 속도 격차 {behind_line.velocity_gap:+.1f}",
                )
            )

        # ---------------------------------------------------------------------
        # R-03: 상대 풀백 체력 저하(<=70%) 또는 경고 누적 → 1:1 매치업 유혈 지점 집중 타격
        # ---------------------------------------------------------------------
        wing_matchups = [m for m in matchups if m.pair_id in ("right_wing_1v1", "left_wing_1v1")]
        for wm in wing_matchups:
            rule_key = f"R-03-{wm.pair_id}"
            is_tired_or_booked = wm.defender_condition <= 70.0 or wm.defender_booked
            if is_tired_or_booked and self._is_active_with_hysteresis(
                rule_key, minute, wm.dribble_prob, on_threshold=66.0, off_threshold=63.0
            ):
                side_kr = "우측" if wm.pair_id == "right_wing_1v1" else "좌측"
                status_tag = f"체력 {wm.defender_condition:.0f}% 저하" + (" + 옐로카드" if wm.defender_booked else "")
                recs.append(
                    TacticalRecommendation(
                        rule_id="R-03",
                        priority="URGENT",
                        category="PLAYER_INSTRUCTION",
                        title=f"[{side_kr} 유혈 지점 포착] {wm.defender_name} ({status_tag}) 집중 돌파",
                        action_badges=[
                            f"{wm.attacker_name} ({wm.attacker_slot}): 드리블 더 많이",
                            f"{side_kr} 측면 집중 공략",
                            f"{side_kr} 오버래핑/언더래핑",
                        ],
                        reasoning=(
                            f"상대 {wm.defender_slot} {wm.defender_name}의 {status_tag}로 실효 민첩성·태클이 급락했습니다. "
                            f"{wm.attacker_name}의 1:1 돌파 성공 기대 확률이 {wm.dribble_prob:.1f}%에 달하므로 온더볼 돌파를 집중 지시하세요."
                        ),
                        trigger_metric=f"돌파 확률 {wm.dribble_prob:.1f}% | 상대 체력 {wm.defender_condition:.0f}%",
                    )
                )

        # ---------------------------------------------------------------------
        # R-04 & R-05: 크로스 유형 최적화 (낮은 크로스 vs 높은/얼리 크로스)
        # ---------------------------------------------------------------------
        st_matchups = [m for m in matchups if m.pair_id in ("striker_vs_lcb", "striker_vs_rcb")]
        if st_matchups:
            avg_aerial = sum(m.aerial_prob for m in st_matchups) / len(st_matchups)
            avg_agility_gap = sum(m.agility_diff for m in st_matchups) / len(st_matchups)

            if avg_aerial <= 44.0 and avg_agility_gap >= 1.8:
                recs.append(
                    TacticalRecommendation(
                        rule_id="R-04",
                        priority="HIGH",
                        category="TEAM_INSTRUCTION",
                        title="상대 장신 센터백 점프거리 무력화 → [낮은 크로스] 전환",
                        action_badges=[
                            "크로스 유형: 낮은 크로스 (Low Crosses)",
                            "페널티 박스 안으로 공을 투입하라",
                        ],
                        reasoning=(
                            f"상대 센터백 대비 공중볼 경합 승률이 {avg_aerial:.1f}%로 열세이지만, 민첩성/발목 반응성 우위(ΔA {avg_agility_gap:+.1f})가 확실합니다. "
                            f"뜬공 크로스를 금지하고 땅볼 빠른 크로스로 상대의 높은 점프거리 스탯을 주사위 굴림에서 배제하세요."
                        ),
                        trigger_metric=f"제공권 승률 {avg_aerial:.1f}% | 민첩성 우위 {avg_agility_gap:+.1f}",
                    )
                )
            elif avg_aerial >= 66.0:
                recs.append(
                    TacticalRecommendation(
                        rule_id="R-05",
                        priority="HIGH",
                        category="TEAM_INSTRUCTION",
                        title="공중볼/제공권 압도 → [높은 크로스] 및 [일찍 크로스]",
                        action_badges=[
                            "크로스 유형: 높은 크로스 (Floated Crosses)",
                            "일찍 크로스를 올려라 (Hit Early Crosses)",
                        ],
                        reasoning=(
                            f"우리 공격진이 상대 수비진 대비 제공권 경합 승률 {avg_aerial:.1f}%로 압도적 우위를 점하고 있습니다. "
                            f"높은 크로스와 얼리 크로스로 박스 내 공중볼 경합 빈도를 극대화하세요."
                        ),
                        trigger_metric=f"제공권 승률 {avg_aerial:.1f}%",
                    )
                )

        # ---------------------------------------------------------------------
        # R-06: 상대 빌드업 구멍(침착성/퍼스트터치/판단력 저하) 압박 트랩 설정
        # ---------------------------------------------------------------------
        trap_targets = [m for m in matchups if m.press_trap_prob >= 68.0]
        if trap_targets:
            worst_def = max(trap_targets, key=lambda m: m.press_trap_prob)
            recs.append(
                TacticalRecommendation(
                    rule_id="R-06",
                    priority="HIGH" if worst_def.press_trap_prob < 75.0 else "URGENT",
                    category="OPPOSITION_INSTRUCTION",
                    title=f"[상대 대응 지시] 빌드업 취약자 {worst_def.defender_name} 집중 압박 트랩",
                    action_badges=[
                        f"{worst_def.defender_name} ({worst_def.defender_slot}): 항상 압박 (Trigger Press)",
                        "태클: 강하게 (Hard Tackling)",
                        "약발로 유도 (Show Onto Weaker Foot)",
                    ],
                    reasoning=(
                        f"상대 {worst_def.defender_name}({worst_def.defender_slot})의 침착성·퍼스트터치·판단력이 낮아 "
                        f"강한 전방 압박 시 빌드업 턴오버 유발 확률이 {worst_def.press_trap_prob:.1f}%입니다. 상대 대응 지시에서 집중 타겟으로 지정하세요."
                    ),
                    trigger_metric=f"압박 턴오버 확률 {worst_def.press_trap_prob:.1f}%",
                )
            )

        # Sort by priority (URGENT -> HIGH -> MEDIUM)
        priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2}
        recs.sort(key=lambda r: priority_order.get(r.priority, 9))
        return recs

