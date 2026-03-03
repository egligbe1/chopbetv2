import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ConfidenceBarProps {
    confidence: number;
    className?: string;
}

export function ConfidenceBar({ confidence, className }: ConfidenceBarProps) {
    // Determine color based on confidence level
    const getColor = (val: number) => {
        if (val >= 85) return 'bg-success';
        if (val >= 70) return 'bg-warning';
        return 'bg-orange-500';
    };

    return (
        <div className={cn("space-y-1.5", className)}>
            <div className="flex justify-between text-xs font-medium">
                <span className="text-muted-foreground uppercase tracking-wider">Confidence</span>
                <span className={cn(
                    confidence >= 85 ? "text-success" :
                        confidence >= 70 ? "text-warning" : "text-orange-500"
                )}>
                    {confidence}%
                </span>
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-muted/50 border border-white/5">
                <div
                    className={cn("h-full transition-all duration-500 ease-out", getColor(confidence))}
                    style={{ width: `${confidence}%` }}
                />
            </div>
        </div>
    );
}
