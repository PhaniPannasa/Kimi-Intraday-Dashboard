import type { SymbolFactorBreakdown } from '@/types/api';
import { ScoreBreakdown } from './ScoreBreakdown';
import { ConfluenceChecklist } from './ConfluenceChecklist';
import { cn } from '@/lib/utils';

export function FactorGrid({ data }: { data: SymbolFactorBreakdown }) {
  return (
    <div className="space-y-3">
      {/* L2 / L3 / L4 */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-3">
          <div className="mb-2 text-fluid-xs font-medium text-[var(--text-tertiary)]">L2 Universe</div>
          <div className="grid grid-cols-2 gap-1 text-fluid-xs">
            <span>F&O: {data.l2_universe.fo_eligible ? 'Eligible' : 'No'}</span>
            <span>Ban: {data.l2_universe.fo_ban ? 'Yes' : 'No'}</span>
            <span>MWPL: {data.l2_universe.mwpl_status}</span>
            <span>Earn: {data.l2_universe.earnings_flag}</span>
            <span className="col-span-2">LQS: {data.l2_universe.liquidity_quality} ({(data.l2_universe.lqs_score * 100).toFixed(0)}%)</span>
          </div>
        </div>

        <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-3">
          <div className="mb-2 text-fluid-xs font-medium text-[var(--text-tertiary)]">L3 Signals</div>
          <div className="grid grid-cols-2 gap-1 text-fluid-xs">
            <span>RSI: {data.l3_signals.rsi.toFixed(1)}</span>
            <span>ADX: {data.l3_signals.adx.toFixed(1)}</span>
            <span>MACD: {data.l3_signals.macd_hist.toFixed(2)}</span>
            <span>ATR%: {data.l3_signals.atr_pct.toFixed(2)}%</span>
            <span>BB: {data.l3_signals.bb_width.toFixed(1)}%</span>
            <span>VWAP: {data.l3_signals.vwap.toFixed(1)}</span>
            <span className={cn(data.l3_signals.ema_aligned ? 'text-[var(--trade-long)]' : 'text-[var(--trade-short)]')}>
              EMA: {data.l3_signals.ema_aligned ? 'Aligned' : 'Misaligned'}
            </span>
            <span className={cn(data.l3_signals.above_vwap ? 'text-[var(--trade-long)]' : 'text-[var(--trade-short)]')}>
              VWAP: {data.l3_signals.above_vwap ? 'Above' : 'Below'}
            </span>
          </div>
        </div>

        <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-3">
          <div className="mb-2 text-fluid-xs font-medium text-[var(--text-tertiary)]">L4 Sector</div>
          <div className="space-y-1 text-fluid-xs">
            <div className="font-medium">{data.l4_sector.sector_name} #{data.l4_sector.rotation_rank}</div>
            <div>RS-Ratio: {data.l4_sector.rs_ratio.toFixed(2)}</div>
            <div>RS-Momentum: {data.l4_sector.rs_momentum.toFixed(2)}</div>
          </div>
        </div>
      </div>

      {/* L5 Score Breakdown */}
      <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-3">
        <div className="mb-2 flex items-center justify-between">
          <span className="text-fluid-xs font-medium text-[var(--text-tertiary)]">L5 Score Breakdown — Total {data.l5_scores.total.toFixed(1)}</span>
          <span className="text-fluid-xs text-[var(--text-secondary)]">{data.l5_scores.regime}</span>
        </div>
        <ScoreBreakdown scores={data.l5_scores} />
      </div>

      {/* L7 Confluence */}
      <div className="rounded-md border border-[var(--border-subtle)] bg-[var(--bg-surface-raised)]/40 p-3">
        <div className="mb-2 text-fluid-xs font-medium text-[var(--text-tertiary)]">L7 Confluence — {data.l7_confluence.score}/{data.l7_confluence.max}</div>
        <ConfluenceChecklist data={data.l7_confluence} />
      </div>
    </div>
  );
}
