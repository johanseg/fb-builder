import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { Loader, Plus, Sparkles, Trash2, CheckCircle2, Eye, LayoutTemplate } from 'lucide-react';
import SafeZonePreview from './SafeZonePreview';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function ModularBlocksBoard({ product }) {
    const { authFetch } = useAuth();
    const { showError, showSuccess } = useToast();
    
    const [modules, setModules] = useState([]);
    const [loading, setLoading] = useState(false);
    
    // Generation Modal State
    const [genModalOpen, setGenModalOpen] = useState(false);
    const [genType, setGenType] = useState('');
    const [genGenerating, setGenGenerating] = useState(false);
    const [genCount, setGenCount] = useState(3);
    const [baseIntro, setBaseIntro] = useState('');
    const [baseBridge, setBaseBridge] = useState('');
    const [previewContent, setPreviewContent] = useState(null);

    // Assembly State
    const [selectedBlocks, setSelectedBlocks] = useState({
        intro: null, bridge: null, core: null, cta: null
    });
    const [assembling, setAssembling] = useState(false);
    const [assembledResult, setAssembledResult] = useState(null);

    useEffect(() => {
        if (product) fetchModules();
    }, [product]);

    const fetchModules = async () => {
        setLoading(true);
        try {
            const res = await authFetch(`${API_URL}/ad-modules/?product_id=${product.id}`);
            if (!res.ok) throw new Error('Failed to fetch modules');
            const data = await res.json();
            setModules(data);
        } catch (err) {
            showError("Could not load Ad Modules: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async (id) => {
        if (!confirm("Are you sure you want to delete this module?")) return;
        try {
            const res = await authFetch(`${API_URL}/ad-modules/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete');
            setModules(modules.filter(m => m.id !== id));
            // clear selection if deleted
            const newSelection = {...selectedBlocks};
            Object.keys(newSelection).forEach(k => {
                if(newSelection[k]?.id === id) newSelection[k] = null;
            });
            setSelectedBlocks(newSelection);
            
            showSuccess("Module deleted");
        } catch (err) {
            showError("Delete failed: " + err.message);
        }
    };

    const openGenModal = (type) => {
        setGenType(type);
        setGenCount(type === 'intro' ? 5 : 3);
        setGenModalOpen(true);
    };

    const handleGenerate = async () => {
        if (genType === 'bridge' && !baseIntro) return showError("Base Intro is required to generate Bridges.");
        if (genType === 'core' && (!baseIntro || !baseBridge)) return showError("Base Intro and Bridge are required for Cores.");
        
        setGenGenerating(true);
        try {
            const res = await authFetch(`${API_URL}/modular-generation/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_id: product.id,
                    module_type: genType,
                    count: genCount,
                    base_intro: baseIntro,
                    base_bridge: baseBridge
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Generation failed');
            
            showSuccess(`Generated ${data.length} new ${genType}s!`);
            setModules([...data, ...modules]); // prepend new
            setGenModalOpen(false);
        } catch(err) {
            showError(err.message);
        } finally {
            setGenGenerating(false);
        }
    };

    const handleSelectBlock = (mod) => {
        setSelectedBlocks(prev => ({
            ...prev,
            [mod.module_type]: prev[mod.module_type]?.id === mod.id ? null : mod
        }));
    };

    const handleAssemble = async () => {
        if (!selectedBlocks.intro || !selectedBlocks.bridge || !selectedBlocks.core || !selectedBlocks.cta) {
            return showError("Must select one of each block type to assemble.");
        }
        
        setAssembling(true);
        try {
             const res = await authFetch(`${API_URL}/naming/assemble`, {
                 method: 'POST',
                 headers: { 'Content-Type': 'application/json' },
                 body: JSON.stringify({
                     intro_id: selectedBlocks.intro.id,
                     bridge_id: selectedBlocks.bridge.id,
                     core_id: selectedBlocks.core.id,
                     cta_id: selectedBlocks.cta.id
                 })
             });
             const data = await res.json();
             if (!res.ok) throw new Error(data.detail || 'Assembly failed');
             setAssembledResult(data);
             showSuccess("Ad script assembled successfully!");
        } catch(err) {
            showError(err.message);
        } finally {
            setAssembling(false);
        }
    };

    const COLUMNS = [
        { id: 'intro', title: 'Intros / Hooks' },
        { id: 'bridge', title: 'Bridges' },
        { id: 'core', title: 'Cores' },
        { id: 'cta', title: 'CTAs' }
    ];

    const formatName = (m) => {
        return m.generation_metadata?.format || m.generation_metadata?.hook_type || 
               m.generation_metadata?.bridge_type || m.generation_metadata?.core_type || 
               m.generation_metadata?.cta_type || "Standard";
    };

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between mt-4">
                <h2 className="text-xl font-bold text-gray-900">Modular Board</h2>
                <div className="flex items-center gap-4">
                    <button onClick={fetchModules} className="text-sm text-purple-600 hover:text-purple-800 font-medium">
                        Refresh Board
                    </button>
                    <button 
                         onClick={handleAssemble}
                         disabled={!selectedBlocks.intro || !selectedBlocks.bridge || !selectedBlocks.core || !selectedBlocks.cta || assembling}
                         className="px-6 py-2 bg-gray-900 hover:bg-black text-white font-bold rounded-lg disabled:opacity-50 transition-colors flex items-center gap-2"
                    >
                        {assembling ? <Loader size={18} className="animate-spin" /> : "Assemble Structure"}
                    </button>
                </div>
            </div>

            {/* Assembly Tracker Panel */}
            <div className="bg-indigo-50 rounded-xl p-4 border border-indigo-100 flex items-center justify-between">
                <div className="flex items-center gap-6">
                    <span className="text-indigo-900 font-bold flex items-center gap-2"><Sparkles size={18}/> Selected Blocks:</span>
                    {COLUMNS.map(col => {
                        const sel = selectedBlocks[col.id];
                        return (
                             <div key={col.id} className={`text-sm px-3 py-1 rounded-md border ${sel ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-400 border-indigo-200'} transition-all`}>
                                 {sel ? formatName(sel).substring(0, 15) : col.title}
                             </div>
                        )
                    })}
                </div>
                {assembledResult && (
                    <button onClick={() => setAssembledResult(null)} className="text-sm text-indigo-600 hover:text-indigo-800 font-bold">Clear Result</button>
                )}
            </div>

            {assembledResult && (
                <div className="bg-white border-2 border-indigo-500 rounded-xl p-6 shadow-md shadow-indigo-100 relative">
                    <div className="absolute top-4 right-4 bg-indigo-100 text-indigo-700 text-xs font-mono px-3 py-1 rounded">
                        {assembledResult.bundle_code}
                    </div>
                    <h3 className="text-lg font-bold text-gray-900 mb-4">Assembled Final Script</h3>
                    <div className="prose prose-sm"><pre className="whitespace-pre-wrap font-sans text-gray-800 bg-gray-50 p-4 rounded-lg border border-gray-100">{assembledResult.assembled_text}</pre></div>
                    <div className="mt-4 flex gap-3">
                        <button className="px-4 py-2 bg-indigo-600 text-white text-sm font-bold rounded-lg hover:bg-indigo-700">Save to Campaign</button>
                        <button className="px-4 py-2 bg-white text-gray-700 border border-gray-300 text-sm font-bold rounded-lg hover:bg-gray-50 flex items-center gap-2" onClick={() => setPreviewContent(assembledResult.assembled_text)}><LayoutTemplate size={16} /> Safe Zones</button>
                    </div>
                </div>
            )}

            {loading ? (
                <div className="py-20 flex justify-center"><Loader className="animate-spin text-purple-600" size={32} /></div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {COLUMNS.map(col => {
                        const colModules = modules.filter(m => m.module_type === col.id);
                        return (
                            <div key={col.id} className="bg-slate-50 rounded-2xl p-4 border border-slate-200 flex flex-col max-h-[800px]">
                                <div className="flex justify-between items-center mb-4 px-1">
                                    <h3 className="font-bold text-slate-800 flex items-center gap-2">
                                        {col.title}
                                        <span className="bg-slate-200 text-slate-600 text-xs px-2 py-0.5 rounded-full">{colModules.length}</span>
                                    </h3>
                                    <button 
                                        onClick={() => openGenModal(col.id)}
                                        className="text-purple-600 hover:bg-purple-100 p-1.5 rounded-md transition-colors"
                                        title={`Generate ${col.title}`}
                                    >
                                        <Plus size={20} />
                                    </button>
                                </div>

                                <div className="flex-1 overflow-y-auto space-y-3 pr-1 pb-2">
                                    {colModules.length === 0 ? (
                                        <div className="text-center py-8 px-4 text-sm text-slate-400 border-2 border-dashed border-slate-200 rounded-xl">
                                            No {col.title.toLowerCase()} found. Click + to generate.
                                        </div>
                                    ) : (
                                        colModules.map(m => {
                                            const isSelected = selectedBlocks[col.id]?.id === m.id;
                                            return (
                                                <div 
                                                    key={m.id} 
                                                    className={`p-4 rounded-xl shadow-sm border group relative cursor-pointer transition-all ${isSelected ? 'bg-indigo-50 border-indigo-400 ring-1 ring-indigo-400' : 'bg-white border-slate-200 hover:border-purple-300'}`}
                                                    onClick={() => handleSelectBlock(m)}
                                                >
                                                    <button 
                                                        onClick={(e) => { e.stopPropagation(); setPreviewContent(m.content); }}
                                                        className="absolute top-2 right-8 p-1 text-gray-400 hover:text-indigo-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                        title="Check Safe Zones"
                                                    >
                                                        <Eye size={14} />
                                                    </button>
                                                    <button 
                                                        onClick={(e) => { e.stopPropagation(); handleDelete(m.id); }}
                                                        className="absolute top-2 right-2 p-1 text-gray-300 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                    <div className="flex items-center gap-2 mb-2">
                                                        {isSelected && <CheckCircle2 size={16} className="text-indigo-600" />}
                                                        <div className="text-xs font-semibold text-purple-600 uppercase tracking-wider truncate mr-6">
                                                            {formatName(m)}
                                                        </div>
                                                    </div>
                                                    <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{m.content}</p>
                                                    
                                                    {isSelected && (col.id === 'intro' || col.id === 'bridge') && (
                                                        <button 
                                                            className="mt-3 w-full py-1.5 bg-white border border-indigo-200 text-indigo-600 text-xs font-bold rounded-lg hover:bg-indigo-50"
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                // Auto fill base intro/bridge for next step
                                                                if(col.id === 'intro') {
                                                                    setBaseIntro(m.content);
                                                                    openGenModal('bridge');
                                                                } else if (col.id === 'bridge') {
                                                                    setBaseIntro(selectedBlocks.intro?.content || 'Needs an intro');
                                                                    setBaseBridge(m.content);
                                                                    openGenModal('core');
                                                                }
                                                            }}
                                                        >
                                                            Build Next Step
                                                        </button>
                                                    )}
                                                </div>
                                            )
                                        })
                                    )}
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Safe Zone Preview Modal */}
            {previewContent && (
                <SafeZonePreview content={previewContent} onClose={() => setPreviewContent(null)} />
            )}

            {/* Generation Modal */}
            {genModalOpen && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl">
                        <h3 className="text-xl font-bold mb-4 capitalize flex items-center gap-2">
                            <Sparkles className="text-purple-600" size={24} />
                            Generate {genType}s
                        </h3>
                        
                        <div className="space-y-4 mb-6">
                            {(genType === 'bridge' || genType === 'core') && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Base Intro (Context)</label>
                                    <textarea 
                                        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 min-h-[80px] text-sm"
                                        placeholder="Paste the intro text this should follow..."
                                        value={baseIntro}
                                        onChange={e => setBaseIntro(e.target.value)}
                                    />
                                </div>
                            )}

                            {genType === 'core' && (
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">Base Bridge (Context)</label>
                                    <textarea 
                                        className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 min-h-[80px] text-sm"
                                        placeholder="Paste the bridge text this should follow..."
                                        value={baseBridge}
                                        onChange={e => setBaseBridge(e.target.value)}
                                    />
                                </div>
                            )}
                            
                            <div>
                                <label className="block text-sm font-medium text-gray-700 mb-1">Number to Generate</label>
                                <input 
                                    type="number" min="1" max="10"
                                    className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500"
                                    value={genCount}
                                    onChange={e => setGenCount(parseInt(e.target.value) || 1)}
                                />
                            </div>
                        </div>

                        <div className="flex justify-end gap-3">
                            <button 
                                onClick={() => setGenModalOpen(false)}
                                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button 
                                onClick={handleGenerate}
                                disabled={genGenerating}
                                className="px-6 py-2 bg-purple-600 text-white font-bold rounded-lg hover:bg-purple-700 transition-colors flex items-center gap-2 disabled:opacity-50"
                            >
                                {genGenerating ? <Loader size={18} className="animate-spin" /> : <Sparkles size={18} />}
                                {genGenerating ? 'Generating...' : 'Start Generation'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
