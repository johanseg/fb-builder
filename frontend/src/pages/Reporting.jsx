import React, { useCallback, useEffect, useState } from 'react';
import { BarChart3, AlertTriangle, Loader } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useBrands } from '../context/BrandContext';
import { useToast } from '../context/ToastContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const money = (value, currency) => new Intl.NumberFormat(undefined, { style: 'currency', currency: currency || 'USD' }).format(Number(value || 0));

export default function Reporting() {
    const { authFetch, hasPermission } = useAuth();
    const { activeBrand } = useBrands();
    const { showError } = useToast();
    const [report, setReport] = useState(null);
    const [loading, setLoading] = useState(false);
    const [syncing, setSyncing] = useState(false);
    const canSync = hasPermission('reporting:sync');

    const loadReport = useCallback(async () => {
        if (!activeBrand?.id) return;
        setLoading(true);
        try {
            const response = await authFetch(`${API_URL}/performance/meta/report?brand_id=${encodeURIComponent(activeBrand.id)}`);
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.detail || 'Could not load Meta reporting');
            setReport(payload);
        } catch (error) {
            setReport(null);
            showError(error.message);
        } finally {
            setLoading(false);
        }
    }, [activeBrand?.id, authFetch, showError]);

    useEffect(() => { loadReport(); }, [loadReport]);

    const syncReport = async () => {
        if (!activeBrand?.id) return;
        setSyncing(true);
        try {
            const response = await authFetch(`${API_URL}/performance/meta/sync?brand_id=${encodeURIComponent(activeBrand.id)}`, { method: 'POST' });
            const payload = await response.json();
            if (!response.ok) throw new Error(payload.detail || 'Could not sync Meta reporting');
            await loadReport();
        } catch (error) {
            showError(error.message);
        } finally {
            setSyncing(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <header className="bg-card p-6 rounded-2xl shadow-sm border border-border flex justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-foreground flex items-center gap-3"><BarChart3 className="text-purple-600" /> Meta Reporting</h1>
                    <p className="text-muted-foreground mt-2">Stored daily Meta Insights for {activeBrand?.name || 'the selected brand'}.</p>
                </div>
                <div className="flex gap-2">
                    {canSync && <button onClick={syncReport} disabled={syncing || loading || !activeBrand} className="px-4 py-2 rounded-lg bg-amber-600 text-white disabled:opacity-50">{syncing ? 'Syncing…' : 'Sync Meta data'}</button>}
                    <button onClick={loadReport} disabled={loading || !activeBrand} className="px-4 py-2 rounded-lg bg-purple-600 text-white disabled:opacity-50">Refresh view</button>
                </div>
            </header>

            {loading ? <div className="py-20 flex justify-center"><Loader className="animate-spin text-purple-600" /></div> : !activeBrand ? (
                <p className="text-muted-foreground">Select a brand to view its reporting.</p>
            ) : !report ? null : <>
                {report.partial && <div className="rounded-xl border border-amber-300 bg-amber-50 text-amber-900 p-4 flex gap-2"><AlertTriangle size={20} /> Partial sync coverage. Recommendations are suppressed until every mapped account reconciles.</div>}
                <section className="grid md:grid-cols-3 gap-4">
                    {report.summaries.map(summary => <div key={summary.currency} className="bg-card border border-border rounded-xl p-5">
                        <p className="text-sm text-muted-foreground">{summary.currency} stored totals</p>
                        <p className="text-2xl font-bold">{money(summary.spend, summary.currency)}</p>
                        <p className="text-sm text-muted-foreground">{Number(summary.impressions).toLocaleString()} impressions · {Number(summary.clicks).toLocaleString()} clicks</p>
                        <p className="text-sm text-muted-foreground">ROAS {summary.roas == null ? '—' : Number(summary.roas).toFixed(2)} · CTR {summary.ctr == null ? '—' : `${Number(summary.ctr).toFixed(2)}%`}</p>
                    </div>)}
                </section>
                <section className="bg-card border border-border rounded-xl overflow-hidden">
                    <div className="p-5 border-b border-border"><h2 className="font-bold text-lg">Read-only recommendations</h2><p className="text-sm text-muted-foreground">These never change delivery, budgets, or ad status.</p></div>
                    {report.recommendations.length === 0 ? <p className="p-5 text-muted-foreground">No stored ad-day data for this range.</p> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left border-b border-border"><th className="p-3">Ad</th><th className="p-3">Spend</th><th className="p-3">Purchases</th><th className="p-3">ROAS</th><th className="p-3">Recommendation</th></tr></thead><tbody>{report.recommendations.map(item => <tr key={item.meta_ad_id} className="border-b border-border/50"><td className="p-3"><div>{item.ad_name || item.meta_ad_id}</div><small className="text-muted-foreground">{item.campaign_name || 'Unknown campaign'}</small></td><td className="p-3">{money(item.spend, item.currency)}</td><td className="p-3">{item.purchases}</td><td className="p-3">{item.roas == null ? '—' : Number(item.roas).toFixed(2)}</td><td className="p-3"><strong>{item.status}</strong><div className="text-muted-foreground">{item.reason}</div></td></tr>)}</tbody></table></div>}
                </section>
            </>}
        </div>
    );
}
