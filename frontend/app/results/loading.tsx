import { Search } from 'lucide-react';

export default function ResultsLoading() {
    return (
        <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
            <Search className="animate-bounce text-primary/50" size={40} />
            <p className="text-muted-foreground">Searching archives...</p>
        </div>
    );
}
