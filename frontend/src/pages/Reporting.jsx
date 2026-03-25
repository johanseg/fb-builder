import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { BarChart, Upload, ArrowUpRight, ArrowDownRight, AlertTriangle, Sparkles, Loader } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function Reporting() {
    const { authFetch } = useAuth();
    const { showError, showSuccess } = useToast();
    
    const [uploading, setUploading] = useState(false);
    const [flags, setFlags] = useState([]);
    const [loadingFlags, setLoadingFlags] = useState(true);
    const [iteratingId, setIteratingId] = useState(null);

    useEffect(() => {
        fetchKillRuleFlags();
    }, []);

    const fetchKillRuleFlags = async () => {
        try {
            const res = await authFetch(`${API_URL}/performance/kill-rule`);
            if (!res.ok) throw new Error("Failed to fetch kill rule flags");
            const data = await res.json();
            setFlags(data);
        } catch (err) {
            showError(err.message);
        } finally {
            setLoadingFlags(false);
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;

        const formData = new FormData();
        formData.append('file', file);

        setUploading(true);
        try {
            const res = await authFetch(`${API_URL}/performance/import`, {
                method: 'POST',
                // Don't set Content-Type header manually when sending FormData
                body: formData
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Failed to import performance data");
            
            showSuccess(data.message);
            fetchKillRuleFlags(); // Refresh the flags
        } catch (err) {
            showError("Upload failed: " + err.message);
        } finally {
            setUploading(false);
            e.target.value = null; // reset
        }
    };

    const handleIterate = async (moduleId) => {
        setIteratingId(moduleId);
        try {
            const res = await authFetch(`${API_URL}/modular-generation/iterate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ module_id: moduleId, count: 3 })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || "Iteration failed");
            
            showSuccess(`Successfully generated ${data.length} variations! View them on the Modular Board.`);
        } catch (err) {
            showError(err.message);
        } finally {
            setIteratingId(null);
        }
    };

    const winners = flags.filter(f => f.status === 'SCALE');
    const losers = flags.filter(f => f.status === 'KILL');

    return (
        <div className="max-w-7xl mx-auto space-y-8">
            <div className="flex justify-between items-center bg-white p-6 md:p-8 rounded-2xl shadow-sm border border-gray-200">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-3">
                        <BarChart size={32} className="text-purple-600" />
                        Performance Intelligence
                    </h1>
                    <p className="text-gray-600">Train the system on real results to identify winning variables.</p>
                </div>
                
                <div className="flex flex-col items-end">
                    <label className={`cursor-pointer px-6 py-3 rounded-xl font-bold text-white transition-colors flex items-center gap-2 ${uploading ? 'bg-purple-400' : 'bg-purple-600 hover:bg-purple-700'}`}>
                        {uploading ? <Loader className="animate-spin" size={20} /> : <Upload size={20} />}
                        {uploading ? 'Processing File...' : 'Import Facebook CSV'}
                        <input type="file" accept=".csv" className="hidden" onChange={handleFileUpload} disabled={uploading} />
                    </label>
                    <p className="text-xs text-gray-500 mt-2">Exports must contain `Ad Name`, `Amount spent (USD)`, and standard funnel events.</p>
                </div>
            </div>

            {loadingFlags ? (
                <div className="py-20 flex justify-center"><Loader className="animate-spin text-purple-600" size={32} /></div>
            ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    {/* SCALING WINS */}
                    <div className="bg-emerald-50 rounded-2xl p-6 md:p-8 border border-emerald-100">
                        <h2 className="text-2xl font-bold text-emerald-900 mb-6 flex items-center gap-2">
                            <Sparkles className="text-emerald-600" />
                            Winning Variables (<span className="text-xl">Fit Score 4-5</span>)
                        </h2>
                        
                        {winners.length === 0 ? (
                            <div className="text-center py-10 bg-white/50 rounded-xl border border-emerald-100 text-emerald-700">
                                No scalable modules found yet. Keep testing!
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {winners.map(flag => (
                                    <div key={flag.module_id} className="bg-white rounded-xl p-5 shadow-sm border border-emerald-200">
                                        <div className="flex justify-between items-start mb-3">
                                            <div>
                                                <span className="bg-emerald-100 text-emerald-800 text-xs font-bold px-2 py-1 rounded uppercase mr-2">{flag.module_type}</span>
                                                <span className="text-sm font-mono text-gray-500">ID: {flag.module_id.substring(0,8)}</span>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-emerald-600 font-bold flex items-center justify-end gap-1"><ArrowUpRight size={16}/> Score: {flag.score}</div>
                                                <div className="text-xs text-gray-500">Spend: ${flag.spend.toFixed(2)}</div>
                                            </div>
                                        </div>
                                        <div className="text-gray-800 text-sm bg-gray-50 p-3 rounded border border-gray-100 mb-3 whitespace-pre-wrap">
                                            {flag.content}
                                        </div>
                                        <div className="flex justify-between items-center text-sm">
                                            <div className="text-emerald-700 font-medium">
                                                💡 {flag.reason}
                                            </div>
                                            <button 
                                                onClick={() => handleIterate(flag.module_id)}
                                                disabled={iteratingId === flag.module_id}
                                                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg text-xs transition-colors flex items-center gap-1 disabled:opacity-50"
                                            >
                                                {iteratingId === flag.module_id ? <Loader className="animate-spin" size={14}/> : <Sparkles size={14}/>}
                                                Iterate Winner
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>

                    {/* KILL RULE */}
                    <div className="bg-red-50 rounded-2xl p-6 md:p-8 border border-red-100">
                        <h2 className="text-2xl font-bold text-red-900 mb-6 flex items-center gap-2">
                            <AlertTriangle className="text-red-500" />
                            7-Day Kill Rule (<span className="text-xl">Fit Score 0-1</span>)
                        </h2>
                        
                        {losers.length === 0 ? (
                            <div className="text-center py-10 bg-white/50 rounded-xl border border-red-100 text-red-700">
                                No underperforming modules flagged.
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {losers.map(flag => (
                                    <div key={flag.module_id} className="bg-white rounded-xl p-5 shadow-sm border border-red-200">
                                        <div className="flex justify-between items-start mb-3">
                                            <div>
                                                <span className="bg-red-100 text-red-800 text-xs font-bold px-2 py-1 rounded uppercase mr-2">{flag.module_type}</span>
                                                <span className="text-sm font-mono text-gray-500">ID: {flag.module_id.substring(0,8)}</span>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-red-600 font-bold flex items-center justify-end gap-1"><ArrowDownRight size={16}/> Score: {flag.score}</div>
                                                <div className="text-xs text-gray-500">Spend: ${flag.spend.toFixed(2)}</div>
                                            </div>
                                        </div>
                                        <div className="text-gray-800 text-sm bg-gray-50 p-3 rounded border border-gray-100 mb-3 whitespace-pre-wrap">
                                            {flag.content}
                                        </div>
                                        <div className="flex justify-between items-center text-sm">
                                            <div className="text-red-700 font-medium w-full">⚠️ {flag.reason}</div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
