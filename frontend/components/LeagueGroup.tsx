import { type Prediction } from '@/lib/api';
import { PredictionCard } from './PredictionCard';
import { Trophy } from 'lucide-react';

interface LeagueGroupProps {
    league: string;
    predictions: Prediction[];
}

export function LeagueGroup({ league, predictions }: LeagueGroupProps) {
    return (
        <div className="space-y-6">
            {/* League header with divider */}
            <div className="flex items-center gap-4 pb-5 border-b border-white/10">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 shadow-inner">
                    <Trophy size={18} className="text-primary" />
                </div>
                <div className="min-w-0">
                    <h2 className="text-xl font-bold tracking-tight truncate">{league}</h2>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-widest mt-0.5">
                        {predictions.length} Top {predictions.length === 1 ? 'Pick' : 'Picks'} Today
                    </p>
                </div>
                <div className="ml-auto shrink-0 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-bold text-muted-foreground tabular-nums">
                    {predictions.length}
                </div>
            </div>

            {/* Cards grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 lg:gap-7">
                {predictions.map((prediction) => (
                    <PredictionCard key={prediction.id} prediction={prediction} />
                ))}
            </div>
        </div>
    );
}
