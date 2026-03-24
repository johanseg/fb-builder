import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Image, Video, Star, TrendingUp, Zap, Wand2, Package, ShoppingBag } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function Dashboard() {
    const { authFetch } = useAuth();
    const [statsData, setStatsData] = useState({
        brands_count: 0,
        products_count: 0,
        generated_ads_count: 0,
        templates_count: 0,
        campaigns_count: 0
    });

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const response = await authFetch(`${API_URL}/dashboard/stats`);
                if (response.ok) {
                    const data = await response.json();
                    setStatsData(data);
                }
            } catch (error) {
                console.error('Failed to fetch dashboard stats:', error);
            }
        };

        fetchStats();
    }, [authFetch]);

    const stats = [
        { label: 'Total Campaigns', value: statsData.campaigns_count, icon: TrendingUp, color: 'from-amber-500 to-orange-600' },
        { label: 'Generated Ads', value: statsData.generated_ads_count, icon: Image, color: 'from-orange-500 to-red-600' },
        { label: 'Active Brands', value: statsData.brands_count, icon: ShoppingBag, color: 'from-amber-600 to-yellow-600' },
        { label: 'Templates', value: statsData.templates_count, icon: Star, color: 'from-yellow-400 to-amber-500' },
    ];

    const quickActions = [
        { label: 'Build Creatives', description: 'Create new image or video ads', icon: Wand2, path: '/build-creatives', color: 'from-amber-500 to-orange-500' },
        { label: 'Manage Brands', description: 'Update brand assets and profiles', icon: ShoppingBag, path: '/brands', color: 'from-orange-500 to-red-500' },
        { label: 'Browse Templates', description: 'Explore winning ad templates', icon: Star, path: '/winning-ads', color: 'from-amber-600 to-yellow-600' },
    ];

    return (
        <div className="w-full">
            {/* Header */}
            <div className="mb-10 mt-4 animate-slide-in">
                <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70 flex items-center gap-4 tracking-tight">
                    <div className="p-3 bg-primary/10 rounded-2xl border border-primary/20 shadow-[0_0_20px_rgba(245,158,11,0.15)]">
                        <LayoutDashboard size={32} className="text-primary drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]" />
                    </div>
                    Dashboard
                </h1>
                <p className="text-muted-foreground mt-3 text-lg">Welcome to your Creative Command Center</p>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
                {stats.map((stat, index) => {
                    const Icon = stat.icon;
                    return (
                        <div key={index} className="glass-card rounded-2xl p-6 relative overflow-hidden group hover:-translate-y-1 transition-all duration-300 hover:shadow-[0_8px_30px_rgba(0,0,0,0.5)]">
                            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full blur-2xl -mr-10 -mt-10 group-hover:bg-primary/10 transition-colors duration-500"></div>
                            <div className="flex items-center justify-between mb-4 relative z-10">
                                <div className={`bg-gradient-to-br ${stat.color} w-14 h-14 rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                                    <Icon className="text-white drop-shadow-md" size={26} />
                                </div>
                            </div>
                            <div className="text-4xl font-bold text-foreground mb-1 relative z-10 tracking-tight text-gradient">{stat.value}</div>
                            <div className="text-sm font-medium text-muted-foreground relative z-10">{stat.label}</div>
                        </div>
                    );
                })}
            </div>

            {/* Quick Actions */}
            <div className="mb-10">
                <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70 mb-6 tracking-tight">Quick Actions</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {quickActions.map((action, index) => {
                        const Icon = action.icon;
                        return (
                            <Link
                                key={index}
                                to={action.path}
                                className="glass-card rounded-2xl p-6 group hover-glow hover:-translate-y-1 transition-all duration-300 overflow-hidden relative"
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-white/0 to-white/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                                <div className={`bg-gradient-to-br ${action.color} w-16 h-16 rounded-xl flex items-center justify-center mb-6 shadow-lg group-hover:scale-110 transition-transform duration-500 relative z-10`}>
                                    <Icon className="text-white drop-shadow-md" size={30} />
                                </div>
                                <h3 className="text-xl font-bold text-foreground mb-2 relative z-10 tracking-tight group-hover:text-primary transition-colors">{action.label}</h3>
                                <p className="text-sm text-muted-foreground relative z-10">{action.description}</p>
                            </Link>
                        );
                    })}
                </div>
            </div>

            {/* Recent Activity */}
            <div className="glass-card rounded-2xl p-8 relative overflow-hidden">
                <div className="absolute top-0 left-0 w-40 h-40 bg-primary/5 rounded-full blur-3xl"></div>
                <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70 mb-6 tracking-tight relative z-10">Recent Activity</h2>
                <div className="text-center py-16 relative z-10">
                    <div className="w-24 h-24 mx-auto mb-6 rounded-full bg-white/5 border border-white/10 flex items-center justify-center shadow-inner">
                        <Zap size={40} className="text-muted-foreground" />
                    </div>
                    <p className="text-lg text-foreground font-medium">No recent activity yet</p>
                    <p className="text-sm mt-3 text-muted-foreground max-w-sm mx-auto">Start creating generated ads and building creatives to populate your activity feed.</p>
                </div>
            </div>
        </div>
    );
}
