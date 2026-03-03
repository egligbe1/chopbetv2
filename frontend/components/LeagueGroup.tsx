import { type Prediction } from '@/lib/api';
import { PredictionCard } from './PredictionCard';
import { Trophy } from 'lucide-react';

interface LeagueGroupProps {
    league: string;
    predictions: Prediction[];
}

export function LeagueGroup({ league, predictions }: LeagueGroupProps) {
    return (
        <div className="space-y-4">
            <div className="flex items-center gap-3 px-2">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-white/5 border border-white/10 shadow-inner">
                    <Trophy size={18} className="text-primary" />
                </div>
                <div>
                    <h2 className="text-lg font-bold tracking-tight">{league}</h2>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-widest">
                        {predictions.length} Best {predictions.length === 1 ? 'Pick' : 'Picks'}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {predictions.map((prediction) => (
                    <PredictionCard key={prediction.id} prediction={prediction} />
                ))}
            </div>
        </div>
    );
}
