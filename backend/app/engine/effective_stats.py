"""
Module 1: Effective Attribute Calculator (실효 능력치 보정 모듈)
Applies non-linear stamina decay gamma(C) and yellow card caution penalties
to convert base profile attributes into real-time in-match effective attributes.
"""
from __future__ import annotations
from app.models.match_state import PlayerAttributes, PlayerState, TeamTacticalState


def compute_stamina_decay_factor(condition: float) -> float:
    """
    Non-linear stamina decay curve gamma(C):
      - C >= 75%: 1.0 (no penalty)
      - 55% <= C < 75%: 1.0 - 0.008 * (75 - C)  (at 70% -> 0.96, at 60% -> 0.88, at 55% -> 0.84)
      - C < 55%: 0.84 - 0.015 * (55 - C)        (at 45% -> 0.69)
    """
    c = max(0.0, min(100.0, condition))
    if c >= 75.0:
        return 1.0
    elif c >= 55.0:
        return round(1.0 - 0.008 * (75.0 - c), 4)
    else:
        return round(max(0.40, 0.84 - 0.015 * (55.0 - c)), 4)


def compute_effective_player_state(player: PlayerState) -> PlayerState:
    """Populate player.effective_attrs and player.stamina_decay_factor in-place."""
    gamma = compute_stamina_decay_factor(player.condition)
    tech_gamma = 0.5 + 0.5 * gamma  # Technical skills decay at half the rate of physical/concentration
    card_mult = 0.85 if player.is_booked else 1.0  # -15% tackling/aggression when booked

    b = player.base_attrs
    eff = PlayerAttributes(
        # Physical (full gamma impact)
        pace=round(max(1.0, b.pace * gamma), 2),
        acceleration=round(max(1.0, b.acceleration * gamma), 2),
        agility=round(max(1.0, b.agility * gamma), 2),
        balance=round(max(1.0, b.balance * gamma), 2),
        jumping_reach=round(max(1.0, b.jumping_reach * (0.65 + 0.35 * gamma)), 2),
        strength=round(max(1.0, b.strength * (0.6 + 0.4 * gamma)), 2),
        stamina=b.stamina,
        # Technical (tech_gamma + card penalty on tackling)
        dribbling=round(max(1.0, b.dribbling * tech_gamma), 2),
        first_touch=round(max(1.0, b.first_touch * tech_gamma), 2),
        passing=round(max(1.0, b.passing * tech_gamma), 2),
        crossing=round(max(1.0, b.crossing * tech_gamma), 2),
        tackling=round(max(1.0, b.tackling * tech_gamma * card_mult), 2),
        marking=round(max(1.0, b.marking * tech_gamma), 2),
        heading=round(max(1.0, b.heading * tech_gamma), 2),
        flair=b.flair,
        # Mental (concentration & positioning suffer heavily under fatigue)
        off_the_ball=round(max(1.0, b.off_the_ball * (0.35 + 0.65 * gamma)), 2),
        positioning=round(max(1.0, b.positioning * (0.4 + 0.6 * gamma)), 2),
        anticipation=round(max(1.0, b.anticipation * tech_gamma), 2),
        decisions=round(max(1.0, b.decisions * tech_gamma), 2),
        composure=round(max(1.0, b.composure * tech_gamma), 2),
        concentration=round(max(1.0, b.concentration * gamma), 2),
        aggression=round(max(1.0, b.aggression * card_mult), 2),
        bravery=b.bravery,
    )
    player.effective_attrs = eff
    player.stamina_decay_factor = gamma
    return player


def apply_effective_stats_to_team(team: TeamTacticalState) -> TeamTacticalState:
    for p in team.players:
        compute_effective_player_state(p)
    return team

