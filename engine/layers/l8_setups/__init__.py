from .orb_15 import assemble_orb_15
from .vwap_reclaim import assemble_vwap_reclaim
from .supertrend_pullback import assemble_supertrend_pullback
from .mean_reversion import assemble_mean_reversion
from .first_hour_breakout import assemble_first_hour_breakout
from .cpr_breakout import assemble_cpr_breakout

SETUP_ASSEMBLERS = {
    1: assemble_orb_15,
    2: assemble_vwap_reclaim,
    3: assemble_supertrend_pullback,
    4: assemble_mean_reversion,
    5: assemble_first_hour_breakout,
    6: assemble_cpr_breakout,
}
