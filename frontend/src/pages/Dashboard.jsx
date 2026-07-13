import React, { useEffect, useState } from 'react';
import { LayoutDashboard, Image, Video, Star, TrendingUp, Zap, Wand2, Package, ShoppingBag, Loader, AlertCircle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const DATE_PRESETS = [
    { value: 'today', label: 'Today' },
    { value: 'yesterday', label: 'Yesterday' },
    { value: 'last_7d', label: 'Last 7 days' },
    { value: 'last_30d', label: 'Last 30 days' },
];

const formatMoney = (value) => `$${Number(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const formatNumber = (value) => Number(value || 0).toLocaleString();

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

    // Cross-account performance overview. Result is keyed by preset so
    // loading state is derived instead of set synchronously in the effect.
    const [datePreset, setDatePreset] = useState('last_7d');
    const [insightsResult, setInsightsResult] = useState(null); // { preset, rows, error }

    useEffect(() => {
        let cancelled = false;
        authFetch(`${API_URL}/facebook/insights/overview?date_preset=${datePreset}`)
            .then(res => {
                if (!res.ok) return res.json().then(err => { throw new Error(err.detail || `Request failed (${res.status})`); });
                return res.json();
            })
            .then(data => { if (!cancelled) setInsightsResult({ preset: datePreset, rows: Array.isArray(data) ? data : [] }); })
            .catch(err => { if (!cancelled) setInsightsResult({ preset: datePreset, error: err.message }); });
        return () => { cancelled = true; };
    }, [authFetch, datePreset]);

    const insightsLoading = !insightsResult || insightsResult.preset !== datePreset;
    const insightsError = insightsResult?.error;
    const insights = insightsResult?.rows || [];
    const okRows = insights.filter(r => !r.error);
    const totals = okRows.reduce((acc, r) => ({
        spend: acc.spend + (r.spend || 0),
        impressions: acc.impressions + (r.impressions || 0),
        clicks: acc.clicks + (r.clicks || 0),
        purchases: acc.purchases + (r.purchases || 0),
    }), { spend: 0, impressions: 0, clicks: 0, purchases: 0 });

    const stats = [
        { label: 'Total Campaigns', value: statsData.campaigns_count, icon: TrendingUp, color: 'from-amber-500 to-orange-600' },
        { label: 'Generated Ads', value: statsData.generated_ads_count, icon: Image, color: 'from-orange-500 to-red-600' },
        { label: 'Products', value: statsData.products_count, icon: Package, color: 'from-amber-600 to-yellow-600' },
        { label: 'Templates', value: statsData.templates_count, icon: Star, color: 'from-yellow-400 to-amber-500' },
    ];

    const quickActions = [
        { label: 'Build Creatives', description: 'Create new image or video ads', icon: Wand2, path: '/build-creatives', color: 'from-amber-500 to-orange-500' },
        { label: 'Customer Profiles', description: 'Manage target audience profiles', icon: Package, path: '/profiles', color: 'from-orange-500 to-red-500' },
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

            {/* Ad Accounts Performance */}
            <div className="glass-card rounded-2xl p-8 mb-10 relative overflow-hidden">
                <div className="flex items-center justify-between mb-6 relative z-10">
                    <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-white to-white/70 tracking-tight">Ad Accounts</h2>
                    <select
                        value={datePreset}
                        onChange={(e) => setDatePreset(e.target.value)}
                        className="px-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground focus:ring-2 focus:ring-amber-500"
                    >
                        {DATE_PRESETS.map(p => (
                            <option key={p.value} value={p.value}>{p.label}</option>
                        ))}
                    </select>
                </div>

                {insightsLoading ? (
                    <div className="flex items-center justify-center gap-2 py-10 text-muted-foreground relative z-10">
                        <Loader className="animate-spin" size={20} />
                        <span>Loading account performance...</span>
                    </div>
                ) : insightsError ? (
                    <div className="flex items-center gap-2 py-6 text-red-400 text-sm relative z-10">
                        <AlertCircle size={18} /> {insightsError}
                    </div>
                ) : (insights || []).length === 0 ? (
                    <p className="text-muted-foreground py-6 relative z-10">No ad accounts found.</p>
                ) : (
                    <div className="overflow-x-auto relative z-10">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-left text-muted-foreground border-b border-border">
                                    <th className="py-2 pr-4 font-medium">Account</th>
                                    <th className="py-2 pr-4 font-medium text-right">Spend</th>
                                    <th className="py-2 pr-4 font-medium text-right">Impressions</th>
                                    <th className="py-2 pr-4 font-medium text-right">Clicks</th>
                                    <th className="py-2 pr-4 font-medium text-right">CPM</th>
                                    <th className="py-2 pr-4 font-medium text-right">CTR</th>
                                    <th className="py-2 pr-4 font-medium text-right">Purchases</th>
                                    <th className="py-2 font-medium text-right">ROAS</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(insights || []).map(row => (
                                    <tr key={row.account_id} className="border-b border-border/50 hover:bg-white/5">
                                        <td className="py-2.5 pr-4 text-foreground">{row.account_name}</td>
                                        {row.error ? (
                                            <td colSpan={7} className="py-2.5 text-red-400 text-xs truncate max-w-xs" title={row.error}>
                                                {row.error}
                                            </td>
                                        ) : (
                                            <>
                                                <td className="py-2.5 pr-4 text-right text-foreground">{formatMoney(row.spend)}</td>
                                                <td className="py-2.5 pr-4 text-right text-muted-foreground">{formatNumber(row.impressions)}</td>
                                                <td className="py-2.5 pr-4 text-right text-muted-foreground">{formatNumber(row.clicks)}</td>
                                                <td className="py-2.5 pr-4 text-right text-muted-foreground">{formatMoney(row.cpm)}</td>
                                                <td className="py-2.5 pr-4 text-right text-muted-foreground">{Number(row.ctr || 0).toFixed(2)}%</td>
                                                <td className="py-2.5 pr-4 text-right text-foreground">{formatNumber(row.purchases)}</td>
                                                <td className="py-2.5 text-right text-foreground">{Number(row.roas || 0).toFixed(2)}</td>
                                            </>
                                        )}
                                    </tr>
                                ))}
                                {okRows.length > 1 && (
                                    <tr className="font-semibold text-foreground">
                                        <td className="py-2.5 pr-4">Total ({okRows.length} accounts)</td>
                                        <td className="py-2.5 pr-4 text-right">{formatMoney(totals.spend)}</td>
                                        <td className="py-2.5 pr-4 text-right">{formatNumber(totals.impressions)}</td>
                                        <td className="py-2.5 pr-4 text-right">{formatNumber(totals.clicks)}</td>
                                        <td className="py-2.5 pr-4 text-right">
                                            {formatMoney(totals.impressions > 0 ? (totals.spend / totals.impressions) * 1000 : 0)}
                                        </td>
                                        <td className="py-2.5 pr-4 text-right">
                                            {(totals.impressions > 0 ? (totals.clicks / totals.impressions) * 100 : 0).toFixed(2)}%
                                        </td>
                                        <td className="py-2.5 pr-4 text-right">{formatNumber(totals.purchases)}</td>
                                        <td className="py-2.5 text-right">—</td>
                                    </tr>
                                )}
                            </tbody>
                        </table>
                    </div>
                )}
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
