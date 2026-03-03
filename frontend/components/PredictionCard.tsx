'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Clock, Info, Trophy, AlertCircle, CheckCircle2, XCircle, ExternalLink } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { ConfidenceBar } from './ConfidenceBar';
import { type Prediction } from '@/lib/api';
import { format } from 'date-fns';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface PredictionCardProps {
    prediction: Prediction;
}

export function PredictionCard({ prediction }: PredictionCardProps) {

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

    return (
        <div className="glass-card hover-glow overflow-hidden transition-all duration-300">
            <div className="p-4 md:p-5">
                {/* Header: Kickoff & League */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                        <Clock size={14} />
                        <span>{format(new Date(prediction.kickoff_time), 'HH:mm')}</span>
                        <span className="mx-1">•</span>
                        <span>{prediction.league}</span>
                    </div>
                    <div className={cn(
                        "px-2 py-0.5 rounded-full text-[10px] font-bold uppercase border",
                        getRiskColor(prediction.risk_rating)
                    )}>
                        {prediction.risk_rating} Risk
                    </div>
                </div>

                {/* Match Teams */}
                <div className="flex flex-col gap-1 mb-5">
                    <h3 className="text-lg font-bold flex items-center justify-between group">
                        <span className="truncate">{prediction.home_team}</span>
                        {prediction.status !== 'pending' && prediction.result && (
                            <span className="text-primary tabular-nums ml-2">
                                {prediction.result.ft_score_home}
                            </span>
                        )}
                    </h3>
                    <h3 className="text-lg font-bold flex items-center justify-between group">
                        <span className="truncate">{prediction.away_team}</span>
                        {prediction.status !== 'pending' && prediction.result && (
                            <span className="text-primary tabular-nums ml-2">
                                {prediction.result.ft_score_away}
                            </span>
                        )}
                    </h3>
                </div>

                {/* Prediction Market */}
                <div className="flex items-center justify-between mb-6 p-3 rounded-lg bg-white/5 border border-white/5">
                    <div className="flex flex-col">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Market</span>
                        <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-foreground/90">{prediction.market}</span>
                            <span className="text-[10px] font-bold text-primary/70 bg-primary/5 px-1.5 py-0.5 rounded border border-primary/10">
                                @{prediction.odds?.toFixed(2) || '1.00'}
                            </span>
                        </div>
                    </div>
                    <div className="flex flex-col items-end">
                        <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-widest">Pick</span>
                        <div className="flex items-center gap-2">
                            <span className="font-bold text-primary text-lg">{prediction.prediction}</span>
                            {statusIcons[prediction.status]}
                        </div>
                    </div>
                </div>

                <ConfidenceBar confidence={prediction.confidence} />
            </div>
        </div>
    );
}
