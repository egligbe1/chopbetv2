'use client';

import { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { formatMarket } from '@/lib/utils';
import { api, type AccuracyStats, type DailyChartData, type LeagueAccuracy, type MarketAccuracy } from '@/lib/api';
import { AccuracyChart } from '@/components/AccuracyChart';
import {
    BarChart3,
    TrendingUp,
    Target,
    Trophy,
    PieChart,
    ShieldCheck,
    Zap,
    Flame,
    AlertCircle
} from 'lucide-react';

export default function StatisticsPage() {
    const [stats, setStats] = useState<AccuracyStats | null>(null);
    const [leagueData, setLeagueData] = useState<LeagueAccuracy | null>(null);
    const [marketData, setMarketData] = useState<MarketAccuracy | null>(null);
    const [chartData, setChartData] = useState<DailyChartData[]>([]);
    const [loading, setLoading] = useState(true);
    const [sport, setSport] = useState<string>('football');

    useEffect(() => {
        async function fetchStats() {
            try {
                setLoading(true);
                const [overall, league, market, daily] = await Promise.all([
                    api.getOverallAccuracy(sport),
                    api.getAccuracyByLeague(sport),
                    api.getAccuracyByMarket(sport),
                    api.getDailyChartData(sport, 14)
                ]);
                setStats(overall);
                setLeagueData(league.by_league);
                setMarketData(market.by_market);
                setChartData(daily.stats);
            } catch (err) {
                console.error('Failed to fetch stats:', err);
            } finally {
                setLoading(false);
            }
        }
        fetchStats();
    }, [sport]);

    if (loading) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
                <div className="h-10 w-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                <p className="text-muted-foreground">Crunching the numbers...</p>
            </div>
        );
    }

    const leagueChart = leagueData ? Object.entries(leagueData).map(([name, data]) => ({
        name,
        accuracy: data.accuracy_pct,
        total: data.total
    })).sort((a, b) => b.accuracy - a.accuracy) : [];

    const marketChart = marketData ? Object.entries(marketData).map(([name, data]) => ({
        name: formatMarket(name),
        accuracy: data.accuracy_pct,
        total: data.total
    })).sort((a, b) => b.accuracy - a.accuracy) : [];

    const trendChart = chartData.map(d => ({
        name: d.date,
        accuracy: d.accuracy_pct,
        total: d.total_predictions
    }));

    return (
        <div className="space-y-6 sm:space-y-10">
            <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
                <div className="space-y-1">
                    <h1 className="text-3xl sm:text-4xl font-black tracking-tight font-outfit">
                        Performance <span className="text-primary">Analytics</span>
                    </h1>
                    <p className="text-sm sm:text-base text-muted-foreground font-medium">
                        Comprehensive breakdown of prediction accuracy.
                    </p>
                </div>
                <div className="flex bg-white/5 rounded-lg p-1 border border-white/10 w-fit shrink-0">
                    <button
                        onClick={() => setSport('football')}
                        className={`px-4 py-2 rounded-md font-bold text-sm transition-colors ${sport === 'football' ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:bg-white/5'}`}
                    >
                        Football
                    </button>
                </div>
            </div>

            {/* Hero Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
                <StatCard
                    label="Overall Accuracy"
                    value={`${stats?.accuracy_pct}%`}
                    subtext={`Across ${stats?.total_predictions} picks`}
                    icon={<ShieldCheck className="text-primary" />}
                />
                <StatCard
                    label="Picks Won"
                    value={stats?.correct || 0}
                    subtext={`Out of ${stats?.total_predictions || 0} Total`}
                    icon={<Zap className="text-yellow-500" />}
                />
                <StatCard
                    label="Best Day"
                    value={`${stats?.best_day?.accuracy_pct || 0}%`}
                    subtext={stats?.best_day?.date || 'N/A'}
                    icon={<Trophy className="text-success" />}
                />
                <StatCard
                    label="Total Days"
                    value={stats?.total_days_tracked || 0}
                    subtext="History tracked"
                    icon={<TrendingUp className="text-primary" />}
                />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-8">
                {/* Trend Chart */}
                <section className="glass-card p-4 sm:p-6 space-y-4 sm:space-y-6">
                    <div className="flex items-center gap-2 sm:gap-3">
                        <div className="p-1.5 sm:p-2 bg-primary/10 rounded-lg"><TrendingUp size={16} className="text-primary sm:w-[18px] sm:h-[18px]" /></div>
                        <h2 className="text-lg sm:text-xl font-bold">Accuracy Trend</h2>
                    </div>
                    <AccuracyChart data={trendChart} type="line" dataKey="accuracy" />
                </section>

                {/* League Breakdown */}
                <section className="glass-card p-4 sm:p-6 space-y-4 sm:space-y-6">
                    <div className="flex items-center gap-2 sm:gap-3">
                        <div className="p-1.5 sm:p-2 bg-primary/10 rounded-lg"><Trophy size={16} className="text-primary sm:w-[18px] sm:h-[18px]" /></div>
                        <h2 className="text-lg sm:text-xl font-bold">Accuracy by League</h2>
                    </div>
                    <AccuracyChart data={leagueChart} dataKey="accuracy" />
                </section>

                {/* Market Breakdown */}
                <section className="glass-card p-4 sm:p-6 space-y-4 sm:space-y-6">
                    <div className="flex items-center gap-2 sm:gap-3">
                        <div className="p-1.5 sm:p-2 bg-primary/10 rounded-lg"><Target size={16} className="text-primary sm:w-[18px] sm:h-[18px]" /></div>
                        <h2 className="text-lg sm:text-xl font-bold">Accuracy by Market</h2>
                    </div>
                    <AccuracyChart data={marketChart} dataKey="accuracy" />
                </section>

                {/* Summary Details */}
                <section className="glass-card p-4 sm:p-6 space-y-4 sm:space-y-6">
                    <div className="flex items-center gap-2 sm:gap-3">
                        <div className="p-1.5 sm:p-2 bg-primary/10 rounded-lg"><BarChart3 size={16} className="text-primary sm:w-[18px] sm:h-[18px]" /></div>
                        <h2 className="text-lg sm:text-xl font-bold">Model Insights</h2>
                    </div>

                    <div className="space-y-4">
                        <div className="p-4 rounded-xl bg-white/5 border border-white/5 flex items-center justify-between">
                            <span className="text-sm font-medium text-muted-foreground">Total Correct</span>
                            <span className="text-lg font-bold text-success font-outfit">{stats?.correct}</span>
                        </div>
                        <div className="p-4 rounded-xl bg-white/5 border border-white/5 flex items-center justify-between">
                            <span className="text-sm font-medium text-muted-foreground">Total Incorrect</span>
                            <span className="text-lg font-bold text-danger font-outfit">{stats?.incorrect}</span>
                        </div>
                        <div className="flex items-start gap-4 p-4 rounded-xl bg-primary/5 border border-primary/10">
                            <AlertCircle size={20} className="text-primary mt-0.5 shrink-0" />
                            <p className="text-xs text-foreground/70 leading-relaxed italic">
                                The accuracy stats are updated every night at 11:00 PM UTC after the Results Checker verifies all pending match outcomes using Google Search.
                            </p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
}

function StatCard({ label, value, subtext, icon }: { label: string, value: string | number, subtext: string, icon: React.ReactNode }) {
    return (
        <div className="glass-card p-3 sm:p-5 space-y-2 sm:space-y-3 relative overflow-hidden group">
            <div className="absolute -right-4 -top-4 opacity-5 group-hover:opacity-10 transition-opacity">
                {icon}
            </div>
            <div className="flex items-center gap-2 text-[10px] sm:text-xs font-bold text-muted-foreground uppercase tracking-widest">
                {label}
            </div>
            <div className="space-y-0.5 sm:space-y-1">
                <h4 className="text-2xl sm:text-3xl font-black font-outfit">{value}</h4>
                <p className="text-[10px] sm:text-xs text-muted-foreground font-medium">{subtext}</p>
            </div>
        </div>
    );
}
