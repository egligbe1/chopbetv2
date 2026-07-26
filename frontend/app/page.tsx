'use client';

import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { api, type DailySummary, type AccumulatorSummary } from '@/lib/api';
import { LeagueGroup } from '@/components/LeagueGroup';
import AccumulatorCard from '@/components/AccumulatorCard';
import { formatMarket, groupAndSortByLeague, parseLocalDate } from '@/lib/utils';
import {
  Trophy,
  Target,
  TrendingUp,
  RefreshCcw,
  AlertCircle,
  BarChart2,
  Zap,
  ChevronDown
} from 'lucide-react';
import { format } from 'date-fns';

export default function HomePage() {
  const [data, setData] = useState<DailySummary | null>(null);
  const [accumulator, setAccumulator] = useState<AccumulatorSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [sport, setSport] = useState<string>('football');
  const [showAccumulator, setShowAccumulator] = useState(false);
  const dataRef = useRef<DailySummary | null>(null);

  const fetchData = useCallback(async (isBackground = false) => {
    try {
      // Only show loading spinner on initial load, not background refreshes
      if (!isBackground) setLoading(true);
      const [summary, acca] = await Promise.all([
        api.getTodayPredictions(sport),
        api.getAccumulator(sport).catch(() => null)
      ]);
      setData(summary);
      dataRef.current = summary;
      setAccumulator(acca);

      // Use the actual backend generation time instead of fetch time
      if (summary?.predictions?.length > 0) {
        setLastUpdated(new Date(summary.predictions[0].created_at));
      } else {
        setLastUpdated(new Date());
      }

      setError(null);
    } catch (err: any) {
      console.error('Fetch error:', err.message || 'Unknown network error');
      // Only show error if we don't have any cached data to display
      if (!dataRef.current) {
        setError('Failed to load predictions. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
  }, [sport]);

  useEffect(() => {
    fetchData();
    // Background refresh every 5 minutes (just reads from DB, doesn't trigger AI).
    // Skip while the tab is hidden so we don't wake Neon / burn requests for
    // backgrounded tabs; refetch immediately when the tab becomes visible again.
    const interval = setInterval(() => {
      if (!document.hidden) fetchData(true);
    }, 5 * 60 * 1000);
    const onVisible = () => {
      if (!document.hidden) fetchData(true);
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [fetchData]);

  // NOTE: all hooks (incl. these useMemos) MUST run before any early return
  // below, or the loading/error returns would change the hook count between
  // renders and crash with React error #310.
  const predictions = useMemo(() => data?.predictions || [], [data]);

  const avgConfidence = useMemo(() => predictions.length > 0
    ? Math.round(predictions.reduce((acc, p) => acc + p.confidence, 0) / predictions.length)
    : 0, [predictions]);

  const sortedLeagueEntries = useMemo(() => groupAndSortByLeague(predictions), [predictions]);

  const marketsCount = useMemo(() => predictions.reduce((acc, p) => {
    acc[p.market] = (acc[p.market] || 0) + 1;
    return acc;
  }, {} as Record<string, number>), [predictions]);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCcw className="animate-spin text-primary" size={40} />
        <p className="text-muted-foreground animate-pulse">Loading today's predictions...</p>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4 text-center max-w-md mx-auto">
        <AlertCircle className="text-danger" size={40} />
        <h2 className="text-xl font-bold">Something went wrong</h2>
        <p className="text-muted-foreground">{error}</p>
        <button
          onClick={() => fetchData()}
          className="mt-2 px-6 py-2 bg-primary text-primary-foreground rounded-lg font-bold hover:opacity-90 transition-opacity"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 sm:space-y-14">
      {/* Hero Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight font-outfit">
            Today's <span className="text-primary">Predictions</span>
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground font-medium">
            {format(new Date(), 'EEEE, MMMM do yyyy')}
          </p>
          <div className="flex bg-white/5 rounded-lg p-1 border border-white/10 w-fit mt-4">
            <button
              onClick={() => setSport('football')}
              className={`px-4 py-2 rounded-md font-bold text-sm transition-colors ${sport === 'football' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-white/5'}`}
            >
              Football
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2 text-xs font-bold text-muted-foreground bg-white/5 px-3 py-1.5 rounded-full border border-white/5 mb-2 md:mb-0">
          <RefreshCcw size={14} className={loading ? "animate-spin" : ""} />
          Generated at: {format(lastUpdated, 'HH:mm')}
        </div>
      </div>

      {/* Top Picks (Super Acca) — hidden until the user asks for it */}
      {accumulator != null && (accumulator.predictions?.length ?? 0) > 0 && (
        <div className="space-y-4">
          <button
            onClick={() => setShowAccumulator((v) => !v)}
            aria-expanded={showAccumulator}
            className="w-full sm:w-auto flex items-center justify-center gap-2 bg-primary/10 hover:bg-primary/20 border border-primary/20 text-primary font-bold px-5 py-3 rounded-xl transition-colors"
          >
            <Zap size={18} className="fill-current" />
            {showAccumulator ? 'Hide Top Picks' : 'Show Daily Super Acca'}
            <ChevronDown size={18} className={`transition-transform ${showAccumulator ? 'rotate-180' : ''}`} />
          </button>
          {showAccumulator && (
            <AccumulatorCard
              predictions={accumulator.predictions}
              totalOdds={accumulator.total_odds}
              date={format(parseLocalDate(accumulator.date), 'MMMM do')}
            />
          )}
        </div>
      )}

      {/* Summary Dashboard */}
      <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-5">
        <SummaryCard
          icon={<Trophy className="text-primary" />}
          label="Total Picks"
          value={predictions.length}
          subtext="High-confidence only"
        />
        <SummaryCard
          icon={<Target className="text-success" />}
          label="Avg Confidence"
          value={`${avgConfidence}%`}
          subtext="Model output"
        />
        <SummaryCard
          icon={<TrendingUp className="text-warning" />}
          label="Top Market"
          value={formatMarket(Object.entries(marketsCount).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A')}
          subtext="Most frequent"
        />
        <SummaryCard
          icon={<BarChart2 className="text-primary" />}
          label="Status"
          value={predictions.some(p => p.status === 'pending') ? "Live" : "Settled"}
          subtext="Daily Progress"
        />
      </div>

      {/* Content Area */}
      {sortedLeagueEntries.length > 0 ? (
        <div className="space-y-10">
          {sortedLeagueEntries.map(([league, preds]) => (
            <LeagueGroup key={league} league={league} predictions={preds} layout="list" />
          ))}
        </div>
      ) : (
        <div className="text-center py-20 glass-card">
          <RefreshCcw size={48} className="mx-auto text-primary/20 mb-4" />
          <h3 className="text-xl font-bold">No predictions yet today</h3>
          <p className="text-muted-foreground">Today's picks are generated around 07:00 UTC — check back soon.</p>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value, subtext }: { icon: React.ReactNode, label: string, value: string | number, subtext: string }) {
  return (
    <div className="glass-card p-3 sm:p-4 md:p-5 flex items-start gap-3 sm:gap-4">
      <div className="h-10 w-10 sm:h-12 sm:w-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 shadow-lg shrink-0">
        {icon}
      </div>
      <div className="min-w-0">
        <span className="text-[10px] sm:text-xs font-bold text-muted-foreground uppercase tracking-wider">{label}</span>
        <h4 className="text-xl sm:text-2xl font-black font-outfit truncate">{value}</h4>
        <p className="text-[10px] text-muted-foreground font-medium">{subtext}</p>
      </div>
    </div>
  );
}
