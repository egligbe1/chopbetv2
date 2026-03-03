'use client';

import { useState, useEffect, useCallback } from 'react';
import { api, type DailySummary, type Prediction } from '@/lib/api';
import { LeagueGroup } from '@/components/LeagueGroup';
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
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchResults = useCallback(async (date: Date) => {
        try {
            setLoading(true);
            const formattedDate = format(date, 'yyyy-MM-dd');
            const results = await api.getPredictionsByDate(formattedDate);
            setData(results);
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

    return (
        <div className="space-y-10">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                <div className="space-y-1">
                    <h1 className="text-4xl font-black tracking-tight font-outfit">
                        Prediction <span className="text-primary">History</span>
                    </h1>
                    <p className="text-muted-foreground font-medium">
                        Analyze past performance and match outcomes.
                    </p>
                </div>

                <div className="glass-card p-4 min-w-[320px]">
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
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

                    {Object.entries(groupedPredictions).map(([league, preds]) => (
                        <LeagueGroup key={league} league={league} predictions={preds} />
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
        <div className="glass-card p-4 flex items-center justify-between border-l-4 border-l-primary/50">
            <div className="flex items-center gap-3">
                <div className={cn("p-2 rounded-lg bg-white/5", color)}>
                    {icon}
                </div>
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">{label}</span>
            </div>
            <span className={cn("text-xl font-black font-outfit", color)}>{value}</span>
        </div>
    );
}
