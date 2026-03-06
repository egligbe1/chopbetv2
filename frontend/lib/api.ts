const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface PredictionResult {
  ht_score_home: number | null;
  ht_score_away: number | null;
  ft_score_home: number | null;
  ft_score_away: number | null;
  result_checked_at: string | null;
}

export interface Prediction {
  id: number;
  date: string;
  home_team: string;
  away_team: string;
  league: string;
  country: string;
  kickoff_time: string;
  market: string;
  prediction: string;
  confidence: number;
  odds: number;
  source_link: string | null;
  reasoning: string;
  risk_rating: string;
  status: 'pending' | 'won' | 'lost' | 'void';
  created_at: string;
  result: PredictionResult | null;
}

export interface AccumulatorSummary {
  date: string;
  total_odds: number;
  count: number;
  predictions: Prediction[];
}

export interface DailySummary {
  date: string;
  count: number;
  settled: number;
  correct: number;
  accuracy_pct: number | null;
  predictions: Prediction[];
}

export interface AccuracyStats {
  total_predictions: number;
  correct: number;
  incorrect: number;
  accuracy_pct: number;
  current_win_streak: number;
  best_day: {
    date: string;
    accuracy_pct: number;
    correct: number;
    total: number;
  } | null;
  worst_day: {
    date: string;
    accuracy_pct: number;
    correct: number;
    total: number;
  } | null;
  total_days_tracked: number;
}

export interface LeagueAccuracy {
  [league: string]: {
    total: number;
    correct: number;
    incorrect: number;
    accuracy_pct: number;
  };
}

export interface MarketAccuracy {
  [market: string]: {
    total: number;
    correct: number;
    incorrect: number;
    accuracy_pct: number;
  };
}

export interface DailyChartData {
  date: string;
  total_predictions: number;
  correct: number;
  incorrect: number;
  accuracy_pct: number;
  by_league: any;
  by_market: any;
}

class ApiClient {
  private async request<T>(endpoint: string, options: RequestInit = {}, retries = 0): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    const isEngineTrigger = endpoint.includes('trigger-predictions') || endpoint.includes('trigger-results');
    // 5 minutes for engine jobs, 60 seconds for regular requests (Neon DB can have cold starts)
    const timeoutMs = isEngineTrigger ? 300000 : 60000;
    // Allow up to 2 retries for regular requests but not for engine triggers
    const maxRetries = isEngineTrigger ? 0 : 2;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const response = await fetch(url, {
        ...options,
        signal: controller.signal,
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `API error: ${response.status}`);
      }

      return await response.json();
    } catch (error: any) {
      if (error.name === 'AbortError') {
        // Retry on timeout for regular requests
        if (retries < maxRetries) {
          console.warn(`Request to ${endpoint} timed out, retrying (${retries + 1}/${maxRetries})...`);
          await new Promise(resolve => setTimeout(resolve, 2000));
          return this.request<T>(endpoint, options, retries + 1);
        }
        throw new Error(`The request timed out. ${isEngineTrigger ? 'The AI Engine is taking a long time but implies it is still processing.' : 'Please try again.'}`);
      }
      // Also retry on network errors for regular requests
      if (retries < maxRetries && !isEngineTrigger) {
        console.warn(`Request to ${endpoint} failed, retrying (${retries + 1}/${maxRetries})...`);
        await new Promise(resolve => setTimeout(resolve, 2000));
        return this.request<T>(endpoint, options, retries + 1);
      }
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  // Predictions
  async getTodayPredictions(sport: string = 'football'): Promise<DailySummary> {
    return this.request<DailySummary>(`/predictions/today?sport=${sport}`);
  }

  async getPredictionsByDate(date: string, sport: string = 'football'): Promise<DailySummary> {
    return this.request<DailySummary>(`/predictions/date/${date}?sport=${sport}`);
  }

  async getAccumulator(sport: string = 'football', date?: string): Promise<AccumulatorSummary> {
    const url = date ? `/predictions/accumulator?sport=${sport}&date=${date}` : `/predictions/accumulator?sport=${sport}`;
    return this.request<AccumulatorSummary>(url);
  }

  async getPredictionHistory(sport: string = 'football', page = 1, perPage = 10): Promise<{
    page: number;
    per_page: number;
    total_days: number;
    total_pages: number;
    days: DailySummary[];
  }> {
    return this.request(`/predictions/history?sport=${sport}&page=${page}&per_page=${perPage}`);
  }

  // Stats
  async getOverallAccuracy(sport: string = 'football'): Promise<AccuracyStats> {
    return this.request<AccuracyStats>(`/stats/accuracy?sport=${sport}`);
  }

  async getAccuracyByLeague(sport: string = 'football'): Promise<{ by_league: LeagueAccuracy }> {
    return this.request(`/stats/accuracy/league?sport=${sport}`);
  }

  async getAccuracyByMarket(sport: string = 'football'): Promise<{ by_market: MarketAccuracy }> {
    return this.request(`/stats/accuracy/market?sport=${sport}`);
  }

  async getDailyChartData(sport: string = 'football', days = 30): Promise<{ stats: DailyChartData[] }> {
    return this.request(`/stats/daily?sport=${sport}&days=${days}`);
  }

  // Admin
  async triggerPredictions(adminKey: string): Promise<{ message: string }> {
    return this.request('/admin/trigger-predictions', {
      method: 'POST',
      headers: { 'X-Admin-Key': adminKey },
    });
  }


  async triggerResults(adminKey: string): Promise<{ message: string }> {
    return this.request('/admin/trigger-results', {
      method: 'POST',
      headers: { 'X-Admin-Key': adminKey },
    });
  }

  async triggerClearPending(adminKey: string): Promise<{ message: string }> {
    return this.request('/admin/clear-pending', {
      method: 'POST',
      headers: { 'X-Admin-Key': adminKey },
    });
  }
}

export const api = new ApiClient();
