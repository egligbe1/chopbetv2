import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export function formatMarket(market: string) {
    if (!market) return market;
    const lowerMarket = market.toLowerCase();

    // BTTS
    if (lowerMarket.includes('btts') || lowerMarket.includes('both teams to score')) return 'BTTS';

    // Double Chance
    if (lowerMarket.includes('double_chance') || lowerMarket.includes('double chance') || (lowerMarket.includes('1x') && lowerMarket !== '1x2') || (lowerMarket.includes('x2') && lowerMarket !== '1x2') || (lowerMarket.includes('12') && lowerMarket !== '1x2')) return 'Double Chance';

    // Draw No Bet
    if (lowerMarket.includes('dnb') || lowerMarket.includes('draw no bet')) return 'Draw No Bet';

    // First Half Over/Under
    if (lowerMarket.includes('ht ') || lowerMarket.includes('1st half') || lowerMarket.includes('first half')) {
        if (lowerMarket.includes('0.5')) return '1st Half Over/Under 0.5';
        if (lowerMarket.includes('1.5')) return '1st Half Over/Under 1.5';
        if (lowerMarket.includes('2.5')) return '1st Half Over/Under 2.5';
    }

    // Over/Under Market handling
    if (lowerMarket.includes('0.5')) return 'Over/Under 0.5';
    if (lowerMarket.includes('1.5')) return 'Over/Under 1.5';
    if (lowerMarket.includes('2.5')) return 'Over/Under 2.5';
    if (lowerMarket.includes('3.5')) return 'Over/Under 3.5';
    if (lowerMarket.includes('4.5')) return 'Over/Under 4.5';

    // Match Winner / 1X2
    if (lowerMarket === '1x2' || lowerMarket.includes('match winner') || lowerMarket === 'home win' || lowerMarket === 'away win' || lowerMarket === 'draw') return '1X2';

    // Capitalize every word as a fallback
    return market.split(/[\s_]+/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

/**
 * Formats a prediction value into a standard, self-descriptive betting label.
 * Handles legacy data where prediction might be "Yes"/"No" instead of "Over 2.5"/"BTTS - Yes".
 */
export function formatPrediction(market: string, prediction: string): string {
    if (!market || !prediction) return prediction || '';
    const lowerMarket = market.toLowerCase();
    const lowerPred = prediction.toLowerCase().trim();

    // Already well-formed? Return as-is (handles new Gemini output)
    if (lowerPred.startsWith('over ') || lowerPred.startsWith('under ') ||
        lowerPred.startsWith('btts') || lowerPred.startsWith('1h ') ||
        lowerPred === '1x' || lowerPred === 'x2' || lowerPred === '12' ||
        lowerPred.includes(' dnb') || lowerPred === 'home win' ||
        lowerPred === 'away win' || lowerPred === 'draw') {
        // Capitalize nicely
        return prediction.trim();
    }

    // --- Legacy normalization: market has detail, prediction is "Yes"/"No" ---

    // Over/Under goals: "Over 2.5 Goals" + "Yes" → "Over 2.5"
    const goalMatch = lowerMarket.match(/(over|under)\s*(\d+\.5)/);
    if (goalMatch) {
        const isFirstHalf = /1st half|first half|ht /i.test(market);
        const prefix = isFirstHalf ? '1H ' : '';
        // If prediction is just "Yes", derive direction from market name
        if (lowerPred === 'yes' || lowerPred === 'over') {
            return `${prefix}Over ${goalMatch[2]}`;
        }
        if (lowerPred === 'no' || lowerPred === 'under') {
            return `${prefix}Under ${goalMatch[2]}`;
        }
        return prediction.trim();
    }

    // Bare threshold in market (e.g. "over_2.5_goals" matched by formatMarket)
    const thresholdMatch = lowerMarket.match(/(\d+\.5)/);
    if (thresholdMatch && (lowerMarket.includes('over') || lowerMarket.includes('under') || lowerMarket.includes('goal'))) {
        const isFirstHalf = /1st half|first half|ht /i.test(market);
        const prefix = isFirstHalf ? '1H ' : '';
        if (lowerPred === 'yes' || lowerPred === 'over') {
            return `${prefix}Over ${thresholdMatch[1]}`;
        }
        if (lowerPred === 'no' || lowerPred === 'under') {
            return `${prefix}Under ${thresholdMatch[1]}`;
        }
        return prediction.trim();
    }

    // BTTS: "BTTS - Yes" or "BTTS" + "Yes" → "BTTS - Yes"
    if (lowerMarket.includes('btts') || lowerMarket.includes('both teams to score')) {
        if (lowerPred === 'yes' || lowerPred === 'y') return 'BTTS - Yes';
        if (lowerPred === 'no' || lowerPred === 'n') return 'BTTS - No';
        return prediction.trim();
    }

    // Double Chance: normalize
    if (lowerMarket.includes('double chance') || lowerMarket.includes('double_chance')) {
        if (lowerPred.includes('1x') || (lowerPred.includes('home') && lowerPred.includes('draw'))) return '1X';
        if (lowerPred.includes('x2') || (lowerPred.includes('away') && lowerPred.includes('draw'))) return 'X2';
        if (lowerPred.includes('12') || (lowerPred.includes('home') && lowerPred.includes('away'))) return '12';
        return prediction.trim();
    }

    // Draw No Bet
    if (lowerMarket.includes('draw no bet') || lowerMarket.includes('dnb')) {
        return prediction.trim();
    }

    // 1X2 / Match Result
    if (lowerMarket === '1x2' || lowerMarket.includes('match winner') || lowerMarket.includes('match result')) {
        if (lowerPred === '1' || lowerPred === 'home') return 'Home Win';
        if (lowerPred === '2' || lowerPred === 'away') return 'Away Win';
        if (lowerPred === 'x' || lowerPred === 'draw') return 'Draw';
        return prediction.trim();
    }

    return prediction.trim();
}
