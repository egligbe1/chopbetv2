'use client';

import { format, subDays, startOfDay, isSameDay } from 'date-fns';
import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface DatePickerProps {
    selectedDate: Date;
    onChange: (date: Date) => void;
}

export function DatePicker({ selectedDate, onChange }: DatePickerProps) {
    // Show the last 7 days as quick picks
    const quickPicks = Array.from({ length: 7 }).map((_, i) => subDays(new Date(), i));

    return (
        <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-primary">
                    <Calendar size={20} />
                    <h3 className="font-bold">Select Date</h3>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => onChange(subDays(selectedDate, 1))}
                        className="p-2 hover:bg-white/5 rounded-full transition-colors border border-white/5"
                    >
                        <ChevronLeft size={18} />
                    </button>
                    <span className="font-bold min-w-[120px] text-center">
                        {isSameDay(selectedDate, new Date()) ? 'Today' : format(selectedDate, 'MMM do, yyyy')}
                    </span>
                    <button
                        onClick={() => onChange(subDays(selectedDate, -1))}
                        disabled={isSameDay(selectedDate, new Date())}
                        className="p-2 hover:bg-white/5 rounded-full transition-colors border border-white/5 disabled:opacity-20 disabled:cursor-not-allowed"
                    >
                        <ChevronRight size={18} />
                    </button>
                </div>
            </div>

            <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
                {quickPicks.map((date) => {
                    const isSelected = isSameDay(date, selectedDate);
                    return (
                        <button
                            key={date.toISOString()}
                            onClick={() => onChange(date)}
                            className={cn(
                                "flex-shrink-0 px-4 py-2 rounded-lg text-xs font-bold transition-all border",
                                isSelected
                                    ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20 scale-105"
                                    : "bg-white/5 text-muted-foreground border-white/5 hover:border-white/20"
                            )}
                        >
                            {isSameDay(date, new Date()) ? 'TODAY' : format(date, 'EEE d').toUpperCase()}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}
