'use client';

import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
    LineChart,
    Line
} from 'recharts';
import { format } from 'date-fns';

interface AccuracyChartProps {
    data: any[];
    type?: 'bar' | 'line';
    dataKey: string;
    nameKey?: string;
}

export function AccuracyChart({ data, type = 'bar', dataKey, nameKey = 'name' }: AccuracyChartProps) {
    const CustomTooltip = ({ active, payload, label }: any) => {
        if (active && payload && payload.length) {
            return (
                <div className="glass-card p-3 border-white/10 shadow-xl">
                    <p className="text-xs font-bold text-muted-foreground uppercase mb-1">{label}</p>
                    <p className="text-lg font-black text-primary">
                        {payload[0].value}% <span className="text-[10px] text-muted-foreground font-medium">Accuracy</span>
                    </p>
                    {payload[0].payload.total && (
                        <p className="text-[10px] text-muted-foreground mt-1">
                            Based on {payload[0].payload.total} predictions
                        </p>
                    )}
                </div>
            );
        }
        return null;
    };

    if (type === 'line') {
        return (
            <div className="h-[300px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={data}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                        <XAxis
                            dataKey={nameKey}
                            stroke="#a3a3a3"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(val) => {
                                try { return format(new Date(val), 'MMM d'); } catch { return val; }
                            }}
                        />
                        <YAxis
                            stroke="#a3a3a3"
                            fontSize={10}
                            tickLine={false}
                            axisLine={false}
                            tickFormatter={(val) => `${val}%`}
                            domain={[0, 100]}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Line
                            type="monotone"
                            dataKey={dataKey}
                            stroke="#3b82f6"
                            strokeWidth={3}
                            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 4 }}
                            activeDot={{ r: 6, strokeWidth: 0 }}
                        />
                    </LineChart>
                </ResponsiveContainer>
            </div>
        );
    }

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
                    <XAxis
                        dataKey={nameKey}
                        stroke="#a3a3a3"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                    />
                    <YAxis
                        stroke="#a3a3a3"
                        fontSize={10}
                        tickLine={false}
                        axisLine={false}
                        tickFormatter={(val) => `${val}%`}
                        domain={[0, 100]}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff05' }} />
                    <Bar dataKey={dataKey} radius={[4, 4, 0, 0]} barSize={30}>
                        {data.map((entry, index) => (
                            <Cell
                                key={`cell-${index}`}
                                fill={entry[dataKey] >= 80 ? '#22c55e' : entry[dataKey] >= 65 ? '#3b82f6' : '#ef4444'}
                            />
                        ))}
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}
