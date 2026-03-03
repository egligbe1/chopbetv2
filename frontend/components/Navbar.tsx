'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LayoutDashboard, History, BarChart3, Info, Trophy, Shield } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

const navItems = [
    { name: 'Today', href: '/', icon: LayoutDashboard },
    { name: 'Results', href: '/results', icon: History },
    { name: 'Statistics', href: '/stats', icon: BarChart3 },
    { name: 'About', href: '/about', icon: Info },
];

export function Navbar() {
    const pathname = usePathname();

    return (
        <nav className="sticky top-0 z-50 w-full border-b border-white/10 bg-background/80 backdrop-blur-md">
            <div className="container mx-auto px-4">
                <div className="flex h-16 items-center justify-between">
                    <Link href="/" className="flex items-center gap-2 text-xl font-bold tracking-tight">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <Trophy size={20} />
                        </div>
                        <span>Chop<span className="text-primary">Bet</span></span>
                    </Link>

                    <div className="hidden md:flex items-center gap-1">
                        {navItems.map((item) => (
                            <Link
                                key={item.href}
                                href={item.href}
                                className={cn(
                                    "flex items-center gap-2 px-4 py-2 rounded-md font-medium transition-colors",
                                    pathname === item.href
                                        ? "bg-primary/10 text-primary"
                                        : "text-muted-foreground hover:text-foreground hover:bg-white/5"
                                )}
                            >
                                <item.icon size={18} />
                                {item.name}
                            </Link>
                        ))}
                    </div>

                    <div className="md:hidden flex items-center gap-4">
                        {/* Mobile menu could be added here */}
                    </div>
                </div>
            </div>
        </nav>
    );
}
