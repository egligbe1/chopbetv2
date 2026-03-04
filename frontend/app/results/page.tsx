'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, type DailySummary, type Prediction, type AccumulatorSummary } from '@/lib/api';
import { LeagueGroup } from '@/components/LeagueGroup';
import AccumulatorCard from '@/components/AccumulatorCard';
import { DatePicker } from '@/components/DatePicker';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import {
    Calendar,
    CheckCircle2,
    XCircle,
    Clock,
    Search,
    ChevronLeft,
    ChevronRight,
    TrendingUp
} from 'lucide-react';
import { format } from 'date-fns';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export default function ResultsPage() {
    const [selectedDate, setSelectedDate] = useState<Date>(new Date());
    const [data, setData] = useState<DailySummary | null>(null);
    const [accumulator, setAccumulator] = useState<AccumulatorSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchResults = useCallback(async (date: Date) => {
        try {
            setLoading(true);
            const formattedDate = format(date, 'yyyy-MM-dd');
            const [results, acca] = await Promise.all([
                api.getPredictionsByDate(formattedDate),
                api.getAccumulator('football', formattedDate).catch(() => null)
            ]);
            setData(results);
            setAccumulator(acca);
            setError(null);
        } catch (err: any) {
            console.error('Fetch error:', err);
            setError('Failed to load historical data.');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchResults(selectedDate);
    }, [selectedDate, fetchResults]);

    const predictions = data?.predictions || [];

    // Group by league
    const groupedPredictions = predictions.reduce((acc, p) => {
        if (!acc[p.league]) acc[p.league] = [];
        acc[p.league].push(p);
        return acc;
    }, {} as Record<string, Prediction[]>);

    // Sort leagues with top ones first
    const LEAGUE_PRIORITY = [
        'Premier League', 'Champions League', 'La Liga', 'Serie A',
        'Bundesliga', 'Ligue 1', 'Europa League'
    ];

    const sortedLeagueEntries = Object.entries(groupedPredictions).sort(([leagueA], [leagueB]) => {
        const idxA = LEAGUE_PRIORITY.findIndex(l => leagueA.toLowerCase().includes(l.toLowerCase()));
        const idxB = LEAGUE_PRIORITY.findIndex(l => leagueB.toLowerCase().includes(l.toLowerCase()));

        if (idxA !== -1 && idxB !== -1) return idxA - idxB;
        if (idxA !== -1) return -1;
        if (idxB !== -1) return 1;
        return leagueA.localeCompare(leagueB);
    });

    return (
        <div className="space-y-8 sm:space-y-10">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 sm:gap-6">
                <div className="space-y-1">
                    <h1 className="text-3xl sm:text-4xl font-black tracking-tight font-outfit">
                        Prediction <span className="text-primary">History</span>
                    </h1>
                    <p className="text-sm sm:text-base text-muted-foreground font-medium">
                        Analyze past performance and match outcomes.
                    </p>
                </div>

                <div className="glass-card p-3 sm:p-4 w-full md:min-w-[320px] md:w-auto">
                    <DatePicker selectedDate={selectedDate} onChange={setSelectedDate} />
                </div>
            </div>

            {loading ? (
                <div className="flex flex-col items-center justify-center py-20 gap-4">
                    <Search className="animate-bounce text-primary/50" size={40} />
                    <p className="text-muted-foreground">Searching archives...</p>
                </div>
            ) : error ? (
                <div className="text-center py-20 glass-card">
                    <p className="text-danger font-bold">{error}</p>
                </div>
            ) : predictions.length > 0 ? (
                <div className="space-y-12">
                    {/* Daily Accuracy Recap */}
                    <div className="grid grid-cols-3 gap-2 sm:gap-4">
                        <StatBox
                            label="Accuracy"
                            value={data?.accuracy_pct ? `${data.accuracy_pct}%` : 'N/A'}
                            icon={<TrendingUp size={16} />}
                            color="text-primary"
                        />
                        <StatBox
                            label="Correct"
                            value={`${data?.correct || 0} / ${data?.settled || 0}`}
                            icon={<CheckCircle2 size={16} />}
                            color="text-success"
                        />
                        <StatBox
                            label="Pending / Void"
                            value={predictions.length - (data?.settled || 0)}
                            icon={<Clock size={16} />}
                            color="text-warning"
                        />
                    </div>

                    {/* Accumulator Section */}
                    {accumulator != null && (accumulator.predictions?.length ?? 0) > 0 && (
                        <AccumulatorCard
                            predictions={accumulator.predictions}
                            totalOdds={accumulator.total_odds}
                            date={format(selectedDate, 'MMMM do')}
                        />
                    )}

                    {sortedLeagueEntries.map(([league, preds]) => (
                        <LeagueGroup key={league} league={league} predictions={preds} layout="list" />
                    ))}
                </div>
            ) : (
                <div className="text-center py-20 glass-card border-dashed">
                    <Calendar size={48} className="mx-auto text-muted-foreground/20 mb-4" />
                    <h3 className="text-xl font-bold">No data for this date</h3>
                    <p className="text-muted-foreground">Try selecting a more recent date from the picker above.</p>
                </div>
            )}

        </div>
    );
}

function StatBox({ label, value, icon, color }: { label: string, value: string | number, icon: React.ReactNode, color: string }) {
    return (
        <div className="glass-card p-3 sm:p-4 flex flex-col sm:flex-row items-center sm:justify-between gap-2 border-l-4 border-l-primary/50 text-center sm:text-left">
            <div className="flex items-center gap-2 sm:gap-3">
                <div className={cn("p-1.5 sm:p-2 rounded-lg bg-white/5", color)}>
                    {icon}
                </div>
                <span className="text-[10px] sm:text-xs font-bold uppercase tracking-widest text-muted-foreground hidden sm:inline">{label}</span>
            </div>
            <div className="flex flex-col items-center sm:items-end">
                <span className={cn("text-lg sm:text-xl font-black font-outfit leading-tight", color)}>{value}</span>
                <span className="text-[9px] sm:text-[10px] text-muted-foreground font-bold uppercase tracking-widest sm:hidden">{label}</span>
            </div>
        </div>
    );
}
