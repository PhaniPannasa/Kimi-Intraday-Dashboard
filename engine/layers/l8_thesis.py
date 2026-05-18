"""L8 Thesis Assembly — orchestrator, cost model application, actionability tier.

Dispatches to l8_setups/ for each setup type's level computation,
then applies cost model + time-decay + actionability tier.
"""
from datetime import datetime, timezone
from typing import Optional

from models.frames import ThesisCard
from models.enums import Direction, SetupType, ActionabilityTier, LiquidityQuality
from layers.l8_setups import SETUP_ASSEMBLERS
from layers.l8_cost_model import (
    compute_brokerage,
    compute_slippage,
    compute_net_rr,
    compute_grade,
)
from layers.l8_time_decay import compute_time_decay
from layers.l7_confluence import L7Confluence


def compute_actionability_tier(
    net_rr: float,
    liquidity_quality: str,
    fo_ban: bool,
    shortability: str,
    direction: Direction,
    confluence_score: int,
) -> ActionabilityTier:
    """Determine actionability tier per spec Section 5.8.

    Tradeable: Clean path + Net R:R >= 1.0 + liquidity >= Good + no blocking flags
    Constrained: Execution path exists but with friction
    Research-Only: No viable retail execution
    """
    has_blocking_flags = fo_ban
    is_good_liquidity = liquidity_quality in ("Excellent", "Good")

    # Cash-only short with no SLB -> Research-Only
    if direction == Direction.SHORT and shortability == "CASH_ONLY":
        return ActionabilityTier.RESEARCH_ONLY

    if net_rr < 0.8:
        return ActionabilityTier.RESEARCH_ONLY

    if net_rr >= 1.0 and is_good_liquidity and not has_blocking_flags and confluence_score >= 3:
        return ActionabilityTier.TRADEABLE

    if net_rr >= 0.8 and not has_blocking_flags:
        return ActionabilityTier.CONSTRAINED

    return ActionabilityTier.RESEARCH_ONLY


def get_setup_expiry(setup_type: SetupType, session_date: datetime) -> datetime:
    """Return clock-based valid_until for each setup type (IST times)."""
    setup_expiry_times = {
        SetupType.ORB_15MIN: (11, 0),
        SetupType.VWAP_RECLAIM: (14, 0),
        SetupType.SUPERTREND_PULLBACK: (14, 30),
        SetupType.MEAN_REVERSION: (13, 30),
        SetupType.FIRST_HOUR_BREAKOUT: (12, 0),
        SetupType.CPR_BREAKOUT: (14, 0),
    }
    hour, minute = setup_expiry_times.get(setup_type, (15, 15))
    return session_date.replace(hour=hour, minute=minute, second=0, microsecond=0)


class L8Thesis:
    """Orchestrates thesis assembly: setup dispatch -> cost model -> time-decay -> grading."""

    def __init__(self):
        self.confluence = L7Confluence()

    def assemble(
        self,
        symbol: str,
        direction: str,
        setup_type: int,
        setup_params: dict,
        confluence_data: dict,
        cost_params: dict | None = None,
        session_start: datetime | None = None,
    ) -> ThesisCard:
        """Assemble a complete thesis card with cost model and grading.

        Args:
            symbol: Stock symbol
            direction: "LONG" or "SHORT"
            setup_type: 1-6 (SetupType enum value)
            setup_params: Dict of params for the specific setup assembler
            confluence_data: Dict with close/high/low/volume/median_volume/ema9/ema20/
                            ema50/atr/price/invalidation/t1/bar_range/median_range/
                            direction/is_opening
            cost_params: Dict with qty/lot_size/futures/liquidity_quality/fo_ban/shortability
            session_start: Session start datetime for clock-based expiry
        """
        direction_enum = Direction(direction)
        setup_enum = SetupType(setup_type)

        # 1. Compute expiry time
        now = datetime.now(timezone.utc)
        valid_until = get_setup_expiry(setup_enum, session_start or now)

        # 2. Dispatch to setup assembler
        assembler = SETUP_ASSEMBLERS.get(setup_type)
        if assembler is None:
            raise ValueError(f"Unknown setup type: {setup_type}")

        thesis = assembler(
            symbol=symbol,
            direction=direction_enum,
            valid_until=valid_until,
            **setup_params,
        )

        # 3. Compute confluence score
        thesis.confluence_score = self.confluence.compute(confluence_data)

        # 4. Apply cost model
        cp = cost_params or {}
        qty = cp.get("qty", 100)
        lot_size = cp.get("lot_size", 50)
        futures = cp.get("futures", True)
        liq_quality = cp.get("liquidity_quality", "Good")
        fo_ban = cp.get("fo_ban", False)
        shortability = cp.get("shortability", "FUTURES_OPTIONS")

        # Compute brokerage for entry->T1 path
        costs = compute_brokerage(
            entry=thesis.trigger,
            exit=thesis.t1,
            qty=qty,
            lot_size=lot_size,
            futures=futures,
            direction=direction,
        )

        # Compute slippage
        normal_slip_bps = compute_slippage(liq_quality, is_stop=False)
        stop_slip_bps = compute_slippage(liq_quality, is_stop=True)

        # Compute Net R:R with spec formula
        rr = compute_net_rr(
            trigger=thesis.trigger,
            t1=thesis.t1,
            invalidation=thesis.invalidation,
            cost_pct=costs["cost_pct"],
            stop_slippage_pct=stop_slip_bps / 10000.0,  # bps -> percentage
        )

        thesis.gross_rr = rr["gross_rr"]
        thesis.net_rr = rr["net_rr"]
        thesis.net_reward = rr["net_reward"]
        thesis.net_risk = rr["net_risk"]
        thesis.cost_breakdown = costs
        thesis.slippage_bps = normal_slip_bps
        thesis.liquidity_quality = LiquidityQuality(liq_quality)

        # 5. Apply time-decay
        thesis.time_decay_multiplier = compute_time_decay(
            setup_enum.name, minutes_since_creation=0
        )

        # 6. Grade
        thesis.grade = compute_grade(thesis.net_rr)

        # 7. Actionability tier
        thesis.actionability_tier = compute_actionability_tier(
            net_rr=thesis.net_rr,
            liquidity_quality=liq_quality,
            fo_ban=fo_ban,
            shortability=shortability,
            direction=direction_enum,
            confluence_score=thesis.confluence_score,
        )

        return thesis
