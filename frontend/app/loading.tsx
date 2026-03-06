import { RefreshCcw } from 'lucide-react';

export default function Loading() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
            <RefreshCcw className="animate-spin text-primary" size={40} />
            <p className="text-muted-foreground animate-pulse">Loading predictions...</p>
        </div>
    );
}
