CREATE MATERIALIZED VIEW IF NOT EXISTS edge_stats_daily
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) as day,
    setup_type,
    regime,
    sector,
    time_bucket as tb,
    direction,
    COUNT(*) as n,
    AVG(CASE WHEN hit THEN 1 ELSE 0 END) as hit_rate,
    AVG(net_return_pct) as avg_net_return,
    STDDEV(net_return_pct) as std_net_return
FROM thesis_outcomes
GROUP BY 1, 2, 3, 4, 5, 6
WITH NO DATA;
