import { type Prediction } from '@/lib/api';
import { PredictionCard } from './PredictionCard';
import { Trophy } from 'lucide-react';

interface LeagueGroupProps {
    league: string;
    predictions: Prediction[];
    layout?: 'grid' | 'list';
}

export function LeagueGroup({ league, predictions, layout = 'grid' }: LeagueGroupProps) {
    return (
        <div className="space-y-4 sm:space-y-6">
            {/* League header with divider */}
            <div className="flex items-center gap-3 sm:gap-4 pb-3 sm:pb-5 border-b border-white/10">
                <div className="flex h-9 w-9 sm:h-11 sm:w-11 shrink-0 items-center justify-center rounded-xl bg-primary/10 border border-primary/20 shadow-inner">
                    <Trophy size={16} className="text-primary sm:w-[18px] sm:h-[18px]" />
                </div>
                <div className="min-w-0">
                    <h2 className="text-lg sm:text-xl font-bold tracking-tight truncate">{league}</h2>
                    <p className="text-[10px] sm:text-xs text-muted-foreground font-medium uppercase tracking-widest mt-0.5">
                        {predictions.length} Top {predictions.length === 1 ? 'Pick' : 'Picks'}
                    </p>
                </div>
            </div>

            {/* Cards wrapper */}
            <div className={layout === 'grid' ? "grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 lg:gap-7" : "flex flex-col gap-2"}>
                {predictions.map((prediction) => (
                    <PredictionCard key={prediction.id} prediction={prediction} layout={layout} />
                ))}
            </div>
        </div>
    );
}
