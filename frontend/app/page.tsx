'use client';

import { useEffect, useState, useCallback } from 'react';
import { api, type DailySummary, type Prediction, type AccumulatorSummary } from '@/lib/api';
import { LeagueGroup } from '@/components/LeagueGroup';
import AccumulatorCard from '@/components/AccumulatorCard';
import {
  Trophy,
  Target,
  TrendingUp,
  RefreshCcw,
  AlertCircle,
  BarChart2
} from 'lucide-react';
import { format } from 'date-fns';

export default function HomePage() {
  const [data, setData] = useState<DailySummary | null>(null);
  const [accumulator, setAccumulator] = useState<AccumulatorSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const [sport, setSport] = useState<string>('football');

  const fetchData = useCallback(async (isBackground = false) => {
    try {
      // Only show loading spinner on initial load, not background refreshes
      if (!isBackground) setLoading(true);
      const [summary, acca] = await Promise.all([
        api.getTodayPredictions(sport),
        api.getAccumulator(sport).catch(() => null)
      ]);
      setData(summary);
      setAccumulator(acca);

      // Use the actual backend generation time instead of fetch time
      if (summary?.predictions?.length > 0) {
        setLastUpdated(new Date(summary.predictions[0].created_at));
      } else {
        setLastUpdated(new Date());
      }

      setError(null);
    } catch (err: any) {
      console.error('Fetch error:', err);
      // Only show error if we don't have any cached data to display
      if (!data) {
        setError('Failed to load predictions. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
  }, [sport, data]);

  useEffect(() => {
    fetchData();
    // Background refresh every 5 minutes (just reads from DB, doesn't trigger AI)
    const interval = setInterval(() => fetchData(true), 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading && !data) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <RefreshCcw className="animate-spin text-primary" size={40} />
        <p className="text-muted-foreground animate-pulse">Analyzing today's matches...</p>
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

  const predictions = data?.predictions || [];
  const avgConfidence = predictions.length > 0
    ? Math.round(predictions.reduce((acc, p) => acc + p.confidence, 0) / predictions.length)
    : 0;

  // Group by league
  const groupedPredictions = predictions.reduce((acc, p) => {
    if (!acc[p.league]) acc[p.league] = [];
    acc[p.league].push(p);
    return acc;
  }, {} as Record<string, Prediction[]>);

  const marketsCount = predictions.reduce((acc, p) => {
    acc[p.market] = (acc[p.market] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="space-y-10">
      {/* Hero Section */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-4xl font-black tracking-tight font-outfit">
            Today's <span className="text-primary">Predictions</span>
          </h1>
          <p className="text-muted-foreground font-medium">
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

      {/* Accumulator Section */}
      {accumulator?.predictions?.length > 0 && (
        <AccumulatorCard
          predictions={accumulator.predictions}
          totalOdds={accumulator.total_odds}
          date={format(new Date(accumulator.date), 'MMMM do')}
        />
      )}

      {/* Summary Dashboard */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
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
          value={Object.entries(marketsCount).sort((a, b) => b[1] - a[1])[0]?.[0] || 'N/A'}
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
      {Object.keys(groupedPredictions).length > 0 ? (
        <div className="space-y-12">
          {Object.entries(groupedPredictions).map(([league, preds]) => (
            <LeagueGroup key={league} league={league} predictions={preds} />
          ))}
        </div>
      ) : (
        <div className="text-center py-20 glass-card">
          <RefreshCcw size={48} className="mx-auto text-primary/20 mb-4" />
          <h3 className="text-xl font-bold">No predictions yet today</h3>
          <p className="text-muted-foreground">The AI engine generates new picks every morning at 07:00 UTC.</p>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ icon, label, value, subtext }: { icon: React.ReactNode, label: string, value: string | number, subtext: string }) {
  return (
    <div className="glass-card p-4 md:p-5 flex items-start gap-4">
      <div className="h-12 w-12 rounded-xl bg-white/5 flex items-center justify-center border border-white/10 shadow-lg">
        {icon}
      </div>
      <div>
        <span className="text-xs font-bold text-muted-foreground uppercase tracking-wider">{label}</span>
        <h4 className="text-2xl font-black font-outfit">{value}</h4>
        <p className="text-[10px] text-muted-foreground font-medium">{subtext}</p>
      </div>
    </div>
  );
}
