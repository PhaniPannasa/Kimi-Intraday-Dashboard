from engine.layers.l8_setups.orb_15 import assemble_orb_15
from engine.layers.l8_setups.vwap_reclaim import assemble_vwap_reclaim
from engine.layers.l8_setups.supertrend_pullback import assemble_supertrend_pullback
from engine.layers.l8_setups.mean_reversion import assemble_mean_reversion
from engine.layers.l8_setups.first_hour_breakout import assemble_first_hour_breakout
from engine.layers.l8_setups.cpr_breakout import assemble_cpr_breakout

SETUP_ASSEMBLERS = {
    1: assemble_orb_15,
    2: assemble_vwap_reclaim,
    3: assemble_supertrend_pullback,
    4: assemble_mean_reversion,
    5: assemble_first_hour_breakout,
    6: assemble_cpr_breakout,
}
