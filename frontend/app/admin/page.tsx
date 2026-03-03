'use client';

import { useState, FormEvent, useEffect } from 'react';
import { api } from '@/lib/api';
import { Shield, Play, RotateCcw, Lock, AlertCircle, CheckCircle2, RefreshCcw, Trash2 } from 'lucide-react';

export default function AdminPage() {
    const [adminKey, setAdminKey] = useState('');
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [loadingKey, setLoadingKey] = useState<string | null>(null);
    const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

    useEffect(() => {
        // Check if key is stored in session storage to persist across reloads
        const storedKey = sessionStorage.getItem('admin_key');
        if (storedKey) {
            setAdminKey(storedKey);
            setIsAuthenticated(true);
        }
    }, []);

    const handleLogin = (e: FormEvent) => {
        e.preventDefault();
        if (adminKey.trim()) {
            sessionStorage.setItem('admin_key', adminKey);
            setIsAuthenticated(true);
        }
    };

    const handleLogout = () => {
        sessionStorage.removeItem('admin_key');
        setAdminKey('');
        setIsAuthenticated(false);
        setMessage(null);
    };

    const triggerJob = async (type: 'predictions' | 'results' | 'clear-pending') => {
        setLoadingKey(type);
        setMessage(null);

        try {
            let response;
            if (type === 'predictions') {
                response = await api.triggerPredictions(adminKey);
            } else if (type === 'results') {
                response = await api.triggerResults(adminKey);
            } else {
                response = await api.triggerClearPending(adminKey);
            }
            setMessage({ type: 'success', text: response.message || `${type} job completed successfully.` });
        } catch (err: any) {
            console.error(`Error triggering ${type}:`, err);
            // If error is related to invalid key, auto-logout
            if (err.message && err.message.toLowerCase().includes('admin key')) {
                handleLogout();
                setMessage({ type: 'error', text: 'Invalid Admin Key. Please log in again.' });
            } else {
                setMessage({ type: 'error', text: err.message || `Failed to trigger ${type} job.` });
            }
        } finally {
            setLoadingKey(null);
        }
    };

    // ----- UI Render logic -----
    // Login State
    if (!isAuthenticated) {
        return (
            <div className="flex flex-col items-center justify-center min-h-[60vh]">
                <div className="glass-card p-8 w-full max-w-md space-y-6">
                    <div className="flex flex-col items-center text-center space-y-2">
                        <div className="h-16 w-16 bg-primary/20 rounded-full flex items-center justify-center mb-2">
                            <Shield className="text-primary w-8 h-8" />
                        </div>
                        <h1 className="text-2xl font-black font-outfit">Admin Access</h1>
                        <p className="text-sm text-muted-foreground">Enter your secure key to access the control panel.</p>
                    </div>

                    {message && message.type === 'error' && (
                        <div className="bg-danger/10 border border-danger/20 text-danger text-sm p-3 rounded-lg flex items-center gap-2">
                            <AlertCircle size={16} />
                            {message.text}
                        </div>
                    )}

                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="space-y-2">
                            <div className="relative">
                                <Lock className="absolute left-3 top-3 text-muted-foreground w-5 h-5" />
                                <input
                                    type="password"
                                    value={adminKey}
                                    onChange={(e) => setAdminKey(e.target.value)}
                                    placeholder="Enter API Key"
                                    className="w-full bg-white/5 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary"
                                    required
                                />
                            </div>
                        </div>
                        <button
                            type="submit"
                            className="w-full bg-primary text-primary-foreground font-bold py-3 rounded-lg hover:opacity-90 transition-opacity"
                        >
                            Authenticate
                        </button>
                    </form>
                </div>
            </div>
        );
    }

    // Dashboard State
    return (
        <div className="space-y-8 max-w-4xl mx-auto">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-black font-outfit flex items-center gap-3">
                        <Shield className="text-primary" /> Admin Control Panel
                    </h1>
                    <p className="text-muted-foreground mt-1">Manage system jobs and manual triggers.</p>
                </div>
                <button
                    onClick={handleLogout}
                    className="text-sm border border-white/10 hover:bg-white/5 px-4 py-2 rounded-lg transition-colors"
                >
                    Logout
                </button>
            </div>

            {message && (
                <div className={`p-4 rounded-lg flex items-start gap-3 border ${message.type === 'success'
                    ? 'bg-success/10 border-success/20 text-success'
                    : 'bg-danger/10 border-danger/20 text-danger'
                    }`}>
                    {message.type === 'success' ? <CheckCircle2 className="mt-0.5 shrink-0" /> : <AlertCircle className="mt-0.5 shrink-0" />}
                    <div>
                        <h4 className="font-bold">{message.type === 'success' ? 'Success' : 'Error'}</h4>
                        <p className="text-sm opacity-90">{message.text}</p>
                    </div>
                </div>
            )}

            <div className="grid md:grid-cols-3 gap-6">
                {/* Football Predictions Trigger Card */}
                <div className="glass-card p-6 space-y-4">
                    <div className="h-12 w-12 bg-primary/20 rounded-xl flex items-center justify-center border border-primary/20 shadow-lg">
                        <Play className="text-primary w-6 h-6" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold">Football Predictions</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Trigger daily AI prediction engine for football matches. Fetches real fixtures, analyzes context via Gemini, and saves predictions.
                        </p>
                    </div>
                    <button
                        onClick={() => triggerJob('predictions')}
                        disabled={loadingKey !== null}
                        className={`w-full py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all ${loadingKey === 'predictions'
                            ? 'bg-primary/50 cursor-wait text-primary-foreground'
                            : 'bg-primary hover:opacity-90 text-primary-foreground'
                            }`}
                    >
                        {loadingKey === 'predictions' ? (
                            <span className="flex items-center gap-2">
                                <RefreshCcw size={18} className="animate-spin" />
                                Triggering...
                            </span>
                        ) : (
                            'Run Engine'
                        )}
                    </button>
                </div>


                {/* Results Trigger Card */}
                <div className="glass-card p-6 space-y-4">
                    <div className="h-12 w-12 bg-secondary/20 rounded-xl flex items-center justify-center border border-secondary/20 shadow-lg">
                        <RotateCcw className="text-secondary w-6 h-6" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold">Check Results</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Trigger results verification job. Checks completed matches and updates prediction statuses and accuracy stats.
                        </p>
                    </div>
                    <button
                        onClick={() => triggerJob('results')}
                        disabled={loadingKey !== null}
                        className={`w-full py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all ${loadingKey === 'results'
                            ? 'bg-secondary/50 cursor-wait text-white'
                            : 'bg-secondary hover:opacity-90 text-white'
                            }`}
                    >
                        {loadingKey === 'results' ? (
                            <span className="flex items-center gap-2">
                                <RefreshCcw size={18} className="animate-spin" />
                                Checking...
                            </span>
                        ) : (
                            'Run Check'
                        )}
                    </button>
                </div>

                {/* Clear Pending Trigger Card */}
                <div className="glass-card p-6 space-y-4">
                    <div className="h-12 w-12 bg-danger/20 rounded-xl flex items-center justify-center border border-danger/20 shadow-lg">
                        <Trash2 className="text-danger w-6 h-6" />
                    </div>
                    <div>
                        <h3 className="text-xl font-bold">Clear Pending</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                            Deletes all pending predictions from the database. Useful for resetting the daily board if stuck.
                        </p>
                    </div>
                    <button
                        onClick={() => triggerJob('clear-pending')}
                        disabled={loadingKey !== null}
                        className={`w-full py-3 rounded-lg font-bold flex items-center justify-center gap-2 transition-all ${loadingKey === 'clear-pending'
                            ? 'bg-danger/50 cursor-wait text-white'
                            : 'bg-danger hover:opacity-90 text-white'
                            }`}
                    >
                        {loadingKey === 'clear-pending' ? (
                            <span className="flex items-center gap-2">
                                <RefreshCcw size={18} className="animate-spin" />
                                Clearing...
                            </span>
                        ) : (
                            'Clear Pending'
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
