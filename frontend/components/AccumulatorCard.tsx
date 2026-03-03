import React from 'react';
import { Prediction } from '../lib/api';
import { TrendingUp, ShieldCheck, Zap, ExternalLink } from 'lucide-react';

interface AccumulatorCardProps {
    predictions: Prediction[];
    totalOdds: number;
    date: string;
}

const AccumulatorCard: React.FC<AccumulatorCardProps> = ({ predictions, totalOdds, date }) => {
    return (
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-indigo-900 via-purple-900 to-indigo-900 p-1 shadow-2xl">
            <div className="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-purple-500/20 blur-3xl"></div>
            <div className="absolute -bottom-20 -left-20 h-64 w-64 rounded-full bg-indigo-500/20 blur-3xl"></div>

            <div className="relative rounded-[22px] bg-slate-950/40 p-6 backdrop-blur-xl lg:p-8">
                <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
                    <div>
                        <div className="flex items-center gap-2 text-indigo-400">
                            <Zap className="h-4 w-4 fill-current" />
                            <span className="text-xs font-bold uppercase tracking-widest">Daily Super Acca</span>
                        </div>
                        <h2 className="mt-1 text-3xl font-black text-white">Chop-Bet Top Picks</h2>
                        <p className="text-sm text-slate-400">Curated high-confidence selection for {date}</p>
                    </div>

                    <div className="flex flex-col items-center rounded-2xl bg-white/10 p-4 text-center backdrop-blur-md">
                        <span className="text-[10px] font-bold uppercase tracking-tighter text-indigo-300">Total Odds</span>
                        <span className="text-4xl font-black text-white">{totalOdds.toFixed(2)}</span>
                    </div>
                </div>

                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                    {predictions.map((p, idx) => (
                        <div key={p.id} className="group relative rounded-2xl bg-slate-900/50 p-4 transition-all hover:bg-slate-800/50">
                            <div className="mb-2 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <span className="text-[10px] font-medium text-slate-500">{p.league}</span>
                                    {p.source_link && (
                                        <a href={p.source_link} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 transition-colors">
                                            <ExternalLink size={10} />
                                        </a>
                                    )}
                                </div>
                                <span className="rounded-md bg-indigo-500/20 px-2 py-0.5 text-xs font-bold text-indigo-300">@{p.odds.toFixed(2)}</span>
                            </div>
                            <div className="text-sm font-bold text-white">
                                {p.home_team} vs {p.away_team}
                            </div>
                            <div className="mt-1 flex items-center gap-2">
                                <span className="text-xs font-semibold text-indigo-400">{p.market}:</span>
                                <span className="text-xs font-black text-white">{p.prediction}</span>
                            </div>

                            {idx < predictions.length - 1 && (
                                <div className="absolute -bottom-2 left-1/2 hidden -translate-x-1/2 md:block">
                                    {/* Visual connector indicator could go here */}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <div className="mt-8 flex items-center justify-center gap-2 rounded-xl bg-indigo-600/20 py-3 text-center">
                    <ShieldCheck className="h-4 w-4 text-indigo-400" />
                    <span className="text-xs font-medium text-indigo-200">AI-Verified High Confidence Selection (90%+ Accuracy Target)</span>
                </div>
            </div>
        </div>
    );
};

export default AccumulatorCard;
