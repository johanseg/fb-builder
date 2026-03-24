import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useBrands } from '../context/BrandContext';
import { useToast } from '../context/ToastContext';
import { Library, Trash2, Loader, Star, Filter } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const MODULE_TABS = [
    { key: 'intro', label: 'Intros', color: 'amber' },
    { key: 'bridge', label: 'Bridges', color: 'blue' },
    { key: 'core', label: 'Cores', color: 'emerald' },
    { key: 'cta', label: 'CTAs', color: 'purple' },
    { key: 'micro_movie', label: 'Micro-Movies', color: 'rose' },
];

export default function AdModulesLibrary() {
    const { authFetch } = useAuth();
    const { activeBrand } = useBrands();
    const { showError, showSuccess } = useToast();

    const [modules, setModules] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('intro');
    const [selectedProductId, setSelectedProductId] = useState('');
    const [deleteTarget, setDeleteTarget] = useState(null);

    const products = activeBrand?.products || [];

    useEffect(() => {
        fetchModules();
    }, [selectedProductId]);

    const fetchModules = async () => {
        setLoading(true);
        try {
            const params = selectedProductId ? `?product_id=${selectedProductId}` : '';
            const res = await authFetch(`${API_URL}/ad-modules/${params}`);
            if (!res.ok) throw new Error('Failed to load modules');
            const data = await res.json();
            setModules(data);
        } catch (err) {
            showError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id) => {
        try {
            const res = await authFetch(`${API_URL}/ad-modules/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Delete failed');
            showSuccess('Module deleted');
            setDeleteTarget(null);
            setModules(prev => prev.filter(m => m.id !== id));
        } catch (err) {
            showError(err.message);
        }
    };

    const filtered = modules.filter(m => m.module_type === activeTab);
    const currentTab = MODULE_TABS.find(t => t.key === activeTab);

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="flex justify-between items-start">
                <div>
                    <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
                        <Library className="text-purple-600" /> Ad Modules Library
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">Browse, filter, and manage all saved modular script blocks.</p>
                </div>

                <div className="flex items-center gap-3">
                    <Filter size={16} className="text-muted-foreground" />
                    <select
                        value={selectedProductId}
                        onChange={e => setSelectedProductId(e.target.value)}
                        className="px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-purple-500 outline-none"
                    >
                        <option value="">All Products</option>
                        {products.map(p => (
                            <option key={p.id} value={p.id}>{p.name}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Tabs */}
            <div className="flex gap-1 bg-secondary p-1 rounded-xl">
                {MODULE_TABS.map(tab => (
                    <button
                        key={tab.key}
                        onClick={() => setActiveTab(tab.key)}
                        className={`flex-1 px-4 py-2.5 rounded-lg text-sm font-bold transition-colors ${
                            activeTab === tab.key
                                ? `bg-card text-${tab.color}-700 shadow-sm`
                                : 'text-muted-foreground hover:text-foreground'
                        }`}
                    >
                        {tab.label}
                        <span className={`ml-2 text-xs px-1.5 py-0.5 rounded-full ${
                            activeTab === tab.key ? `bg-${tab.color}-100 text-${tab.color}-700` : 'bg-muted text-muted-foreground'
                        }`}>
                            {modules.filter(m => m.module_type === tab.key).length}
                        </span>
                    </button>
                ))}
            </div>

            {/* Module Cards */}
            {loading ? (
                <div className="flex justify-center py-16"><Loader className="animate-spin text-purple-600" size={32} /></div>
            ) : filtered.length === 0 ? (
                <div className="bg-card rounded-2xl border border-border p-12 text-center">
                    <Library className="mx-auto text-gray-300 mb-4" size={48} />
                    <h3 className="text-lg font-bold text-foreground mb-2">No {currentTab?.label?.toLowerCase()} found</h3>
                    <p className="text-muted-foreground">Generate modules from the Modular Matrix page to populate this library.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filtered.map(mod => {
                        const meta = mod.generation_metadata || {};
                        const codeLabel = meta.hook_type || meta.bridge_type || meta.core_type || meta.cta_type || mod.module_type;
                        const score = mod.performance_score;

                        return (
                            <div key={mod.id} className="bg-card rounded-xl border border-border p-5 hover:shadow-md transition-shadow group relative">
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        <span className={`text-xs font-bold px-2 py-1 rounded bg-${currentTab?.color}-100 text-${currentTab?.color}-700 uppercase`}>
                                            {codeLabel}
                                        </span>
                                        {score > 0 && (
                                            <span className={`text-xs font-bold px-2 py-1 rounded flex items-center gap-1 ${
                                                score >= 4 ? 'bg-emerald-100 text-emerald-700' : score <= 1 ? 'bg-red-100 text-red-700' : 'bg-secondary text-muted-foreground'
                                            }`}>
                                                <Star size={12} /> {score}/5
                                            </span>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => setDeleteTarget(mod)}
                                        className="p-1.5 text-muted-foreground hover:text-red-600 rounded-lg hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>

                                <p className="text-sm text-foreground line-clamp-4 whitespace-pre-wrap bg-secondary p-3 rounded-lg border border-border">
                                    {mod.content}
                                </p>

                                <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
                                    <span>ID: {mod.id.substring(0, 8)}</span>
                                    <span>{new Date(mod.created_at).toLocaleDateString()}</span>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Delete Confirmation Modal */}
            {deleteTarget && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-card rounded-2xl p-6 shadow-2xl max-w-sm w-full">
                        <h2 className="text-lg font-bold text-foreground mb-2">Delete Module</h2>
                        <p className="text-sm text-muted-foreground mb-1">Are you sure you want to delete this <strong>{deleteTarget.module_type}</strong> module?</p>
                        <p className="text-xs text-muted-foreground mb-6 line-clamp-2">{deleteTarget.content}</p>
                        <div className="flex justify-end gap-3">
                            <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 bg-secondary text-foreground font-bold rounded-xl hover:bg-muted">Cancel</button>
                            <button onClick={() => handleDelete(deleteTarget.id)} className="px-4 py-2 bg-red-600 text-white font-bold rounded-xl hover:bg-red-700">Delete</button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
