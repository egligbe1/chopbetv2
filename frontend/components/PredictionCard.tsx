'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Clock, Info, Trophy, AlertCircle, CheckCircle2, XCircle, ExternalLink } from 'lucide-react';
import { twMerge } from 'tailwind-merge';
import { ConfidenceBar } from './ConfidenceBar';
import { type Prediction } from '@/lib/api';
import { format } from 'date-fns';

import { formatMarket, cn } from '@/lib/utils';

interface PredictionCardProps {
    prediction: Prediction;
    layout?: 'grid' | 'list';
}

export function PredictionCard({ prediction, layout = 'grid' }: PredictionCardProps) {

    const getRiskColor = (risk: string) => {
        switch (risk.toLowerCase()) {
            case 'low': return 'text-success bg-success/10 border-success/20';
            case 'medium': return 'text-warning bg-warning/10 border-warning/20';
            case 'high': return 'text-danger bg-danger/10 border-danger/20';
            default: return 'text-muted-foreground bg-muted/10 border-white/10';
        }
    };

    const statusIcons = {
        won: <CheckCircle2 className="text-success" size={20} />,
        lost: <XCircle className="text-danger" size={20} />,
        pending: <Clock className="text-warning" size={20} />,
        void: <AlertCircle className="text-muted-foreground" size={20} />,
    };

    if (layout === 'list') {
        return (
            <div className="group bg-white/[0.02] hover:bg-white/[0.05] border border-white/[0.05] rounded-xl transition-all overflow-hidden">
                {/* Main fixture row */}
                <div className="flex items-center p-3 gap-2 sm:gap-3">
                    {/* Time */}
                    <div className="text-[11px] text-muted-foreground font-semibold w-10 shrink-0 text-center tabular-nums">
                        {format(new Date(prediction.kickoff_time), 'HH:mm')}
                    </div>

                    {/* Teams + Score */}
                    <div className="flex items-center flex-1 min-w-0">
                        <span className="flex-1 text-right font-bold text-[13px] pr-2 truncate transition-colors group-hover:text-white">
                            {prediction.home_team}
                        </span>

                        <div className="px-2 py-1 w-[56px] shrink-0 flex justify-center items-center font-black text-[13px] bg-black/20 rounded-md border border-white/5">
                            {prediction.status !== 'pending' && prediction.result
                                ? <span className="text-primary tabular-nums">{prediction.result.ft_score_home}-{prediction.result.ft_score_away}</span>
                                : <span className="text-muted-foreground/40 text-[10px]">vs</span>}
                        </div>

                        <span className="flex-1 text-left font-bold text-[13px] pl-2 truncate transition-colors group-hover:text-white">
                            {prediction.away_team}
                        </span>
                    </div>

                    {/* Status icon */}
                    <div className="shrink-0 w-5 flex justify-center">
                        {prediction.status === 'won' && <CheckCircle2 className="text-success" size={16} />}
                        {prediction.status === 'lost' && <XCircle className="text-danger" size={16} />}
                        {prediction.status === 'pending' && <Clock className="text-warning" size={16} />}
                        {prediction.status === 'void' && <AlertCircle className="text-muted-foreground" size={16} />}
                    </div>
                </div>

                {/* Prediction detail strip */}
                <div className="flex items-center justify-between px-3 py-2 bg-white/[0.02] border-t border-white/[0.03]">
                    <div className="flex items-center gap-2 min-w-0">
                        <span className="text-[10px] text-muted-foreground font-bold uppercase tracking-widest shrink-0">{formatMarket(prediction.market)}</span>
                        <span className="text-[10px] text-white/20">•</span>
                        <span className="text-[12px] font-bold text-primary truncate">{prediction.prediction}</span>
                    </div>
                    <span className="px-2 py-0.5 bg-white/5 text-primary/80 rounded text-[11px] font-bold border border-white/10 shrink-0 tabular-nums ml-2">
                        {prediction.odds?.toFixed(2) || '1.00'}
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div className="glass-card hover-glow overflow-hidden transition-all duration-300">
            <div className="p-3 sm:p-4 md:p-5">
                {/* Header: Kickoff & League */}
                <div className="flex items-center justify-between mb-3 sm:mb-4">
                    <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        <Clock size={12} className="sm:w-[14px] sm:h-[14px]" />
                        <span>{format(new Date(prediction.kickoff_time), 'HH:mm')}</span>
                        <span className="mx-0.5 sm:mx-1">•</span>
                        <span className="truncate max-w-[120px] sm:max-w-none">{prediction.league}</span>
                    </div>
                    <div className={cn(
                        "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border",
                        getRiskColor(prediction.risk_rating)
                    )}>
                        {prediction.risk_rating} Risk
                    </div>
                </div>

                {/* Match Teams */}
                <div className="flex flex-col gap-0.5 sm:gap-1 mb-3 sm:mb-5">
                    <h3 className="text-base sm:text-lg font-bold flex items-center justify-between">
                        <span className="truncate">{prediction.home_team}</span>
                        {prediction.status !== 'pending' && prediction.result && (
                            <span className="text-primary tabular-nums ml-2">
                                {prediction.result.ft_score_home}
                            </span>
                        )}
                    </h3>
                    <h3 className="text-base sm:text-lg font-bold flex items-center justify-between">
                        <span className="truncate">{prediction.away_team}</span>
                        {prediction.status !== 'pending' && prediction.result && (
                            <span className="text-primary tabular-nums ml-2">
                                {prediction.result.ft_score_away}
                            </span>
                        )}
                    </h3>
                </div>

                {/* Prediction Market */}
                <div className="flex items-center justify-between mb-3 sm:mb-4 p-2.5 sm:p-3 rounded-lg bg-white/5 border border-white/5">
                    <div className="flex flex-col flex-1 pl-1">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest mb-1">{formatMarket(prediction.market)}</span>
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-primary/80 bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                                @{prediction.odds?.toFixed(2) || '1.00'}
                            </span>
                        </div>
                    </div>
                    <div className="flex flex-col items-end flex-1 pr-1 border-l border-white/10">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest mb-1">Pick</span>
                        <div className="flex items-center gap-2">
                            <span className="font-black text-primary text-base leading-none">{prediction.prediction}</span>
                            <div className="shrink-0">{statusIcons[prediction.status]}</div>
                        </div>
                    </div>
                </div>

                <ConfidenceBar confidence={prediction.confidence} />
            </div>
        </div>
    );
}
