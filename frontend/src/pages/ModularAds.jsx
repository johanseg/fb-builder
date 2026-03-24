import React, { useState } from 'react';
import { Grid3X3, Video, FileSpreadsheet } from 'lucide-react';
import { useBrands } from '../context/BrandContext';
import ModularBlocksBoard from '../components/ModularBlocksBoard';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function ModularAds() {
    const { brands } = useBrands();
    const { authFetch } = useAuth();
    const { showError, showSuccess } = useToast();
    
    const [selectedBrand, setSelectedBrand] = useState('');
    const [selectedProduct, setSelectedProduct] = useState('');
    const [generationType, setGenerationType] = useState('matrix'); // matrix or micro_movie
    const [microMovies, setMicroMovies] = useState(null);
    const [generating, setGenerating] = useState(false);
    const [avatarType, setAvatarType] = useState('');
    const [personas, setPersonas] = useState([]);

    const activeBrand = brands.find(b => b.id === selectedBrand);
    const availableProducts = activeBrand?.products || [];
    const activeProduct = availableProducts.find(p => p.id === selectedProduct);

    React.useEffect(() => {
        if (activeBrand) {
            authFetch(`${API_URL}/personas/?brand_id=${activeBrand.id}`)
                .then(res => res.json())
                .then(data => setPersonas(data))
                .catch(err => console.error("Could not fetch personas", err));
        } else {
            setPersonas([]);
        }
    }, [activeBrand, authFetch]);

    const handleGenerateMicroMovie = async () => {
        if (!activeProduct) return;
        setGenerating(true);
        try {
            const response = await authFetch(`${API_URL}/modular-generation/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_id: activeProduct.id,
                    module_type: 'micro_movie',
                    count: 3,
                    avatar_type: avatarType
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Failed to generate micro movies');

            setMicroMovies(data);
        } catch (err) {
            showError(err.message);
        } finally {
            setGenerating(false);
        }
    };

    return (
        <div className="max-w-7xl mx-auto space-y-6">
            <div className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
                        <Grid3X3 className="text-purple-600" size={32} />
                        Modular Script Factory
                    </h1>
                    <p className="text-gray-600 mt-2">Generate high-volume script variations using knowledge-driven agents.</p>
                </div>
                {activeProduct && generationType === 'matrix' && (
                    <button 
                        onClick={async () => {
                            if (!activeProduct) return;
                            try {
                                const res = await authFetch(`${API_URL}/naming/export-combinations/${activeProduct.id}`);
                                const data = await res.json();
                                if (!res.ok) throw new Error(data.detail || "Export failed");
                                
                                if (data.length === 0) {
                                    return showError("No complete combinations found. Ensure you have generated at least one Intro, Bridge, Core, and CTA.");
                                }
                                
                                const headers = Object.keys(data[0]);
                                const csvRows = [];
                                csvRows.push(headers.join(','));
                                
                                for (const row of data) {
                                    const values = headers.map(h => {
                                        const mapped = (row[h] || "").toString().replace(/"/g, '""');
                                        return `"${mapped}"`;
                                    });
                                    csvRows.push(values.join(','));
                                }
                                
                                const csvString = csvRows.join('\n');
                                const blob = new Blob([csvString], { type: 'text/csv' });
                                const url = window.URL.createObjectURL(blob);
                                const a = document.createElement('a');
                                a.setAttribute('hidden', '');
                                a.setAttribute('href', url);
                                a.setAttribute('download', `Campaign_Export_${activeProduct.name.replace(/\\s+/g, '_')}_PDCA.csv`);
                                document.body.appendChild(a);
                                a.click();
                                document.body.removeChild(a);
                                
                                showSuccess(`Exported ${data.length} structural ad combinations via PDCA!`);
                            } catch (err) {
                                showError("Export failed: " + err.message);
                            }
                        }}
                        className="flex items-center gap-2 px-6 py-2.5 bg-emerald-600 shadow-md text-white font-bold rounded-xl hover:bg-emerald-700 transition"
                    >
                        <FileSpreadsheet size={18} />
                        Export PDCA Campaign
                    </button>
                )}
            </div>

            <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 md:p-8">
                <h2 className="text-xl font-bold text-gray-900 mb-6 border-b border-gray-100 pb-4">1. Select Product Knowledge Base</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Brand</label>
                        <select 
                            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500"
                            value={selectedBrand} 
                            onChange={e => { setSelectedBrand(e.target.value); setSelectedProduct(''); }}
                        >
                            <option value="">Select Brand...</option>
                            {brands.map(b => (
                                <option key={b.id} value={b.id}>{b.name}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Product</label>
                        <select 
                            className="w-full p-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
                            value={selectedProduct} 
                            onChange={e => setSelectedProduct(e.target.value)}
                            disabled={!selectedBrand}
                        >
                            <option value="">Select Product...</option>
                            {availableProducts.map(p => (
                                <option key={p.id} value={p.id}>{p.name}</option>
                            ))}
                        </select>
                        <p className="text-xs text-gray-500 mt-2">Note: The product MUST have a completed Product Brief.</p>
                    </div>
                </div>

                {activeProduct && (
                    <>
                        <h2 className="text-xl font-bold text-gray-900 mb-6 border-b border-gray-100 pb-4">2. Generation Mode</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                            <button
                                onClick={() => setGenerationType('matrix')}
                                className={`p-6 rounded-xl border-2 text-left transition-all ${generationType === 'matrix' ? 'border-purple-600 bg-purple-50' : 'border-gray-200 hover:border-purple-300'}`}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <Grid3X3 className={generationType === 'matrix' ? 'text-purple-600' : 'text-gray-500'} />
                                    <h3 className={`font-bold ${generationType === 'matrix' ? 'text-purple-900' : 'text-gray-700'}`}>Modular Blocks Mode</h3>
                                </div>
                                <p className="text-sm text-gray-600">Generate isolated Intros, Bridges, Cores, and CTAs to build custom combinations.</p>
                            </button>

                            <button
                                onClick={() => setGenerationType('micro_movie')}
                                className={`p-6 rounded-xl border-2 text-left transition-all ${generationType === 'micro_movie' ? 'border-purple-600 bg-purple-50' : 'border-gray-200 hover:border-purple-300'}`}
                            >
                                <div className="flex items-center gap-3 mb-2">
                                    <Video className={generationType === 'micro_movie' ? 'text-purple-600' : 'text-gray-500'} />
                                    <h3 className={`font-bold ${generationType === 'micro_movie' ? 'text-purple-900' : 'text-gray-700'}`}>Micro-Movie Mode</h3>
                                </div>
                                <p className="text-sm text-gray-600">Generates 30-60s emotional storytelling scripts using avatar models.</p>
                            </button>
                        </div>
                    </>
                )}
            </div>

            {activeProduct && generationType === 'matrix' && (
                <ModularBlocksBoard product={activeProduct} />
            )}

            {activeProduct && generationType === 'micro_movie' && (
                <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 md:p-8 space-y-6">
                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-4">
                            <h2 className="text-xl font-bold text-gray-900">Micro-Movie Scripts</h2>
                            <select 
                                value={avatarType} 
                                onChange={e => setAvatarType(e.target.value)}
                                className="p-2 border border-gray-300 rounded-lg text-sm focus:ring-purple-500 max-w-[300px]"
                            >
                                <option value="">Mixed Diverse Avatars</option>
                                <optgroup label="Custom AI Personas">
                                    {personas.map(p => (
                                        <option key={p.id} value={`Persona: ${p.name}. Voice Guidelines: ${p.voice_guidelines}`}>
                                            {p.name}
                                        </option>
                                    ))}
                                </optgroup>
                                <optgroup label="Default Personas">
                                    {['The Relieved Problem-Solver', 'The Skeptical Professional', 'The Overwhelmed Parent', 'The Value Hunter', 'The Tech-Savvy Early Adopter', 'The Burned-Out Operator'].map(def => (
                                        <option key={def} value={def}>{def}</option>
                                    ))}
                                </optgroup>
                            </select>
                        </div>
                        <button
                            onClick={handleGenerateMicroMovie}
                            disabled={generating}
                            className="px-6 py-2 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-xl disabled:opacity-50"
                        >
                            {generating ? 'Agents are writing...' : 'Generate 3 Micro-Movies'}
                        </button>
                    </div>

                    {microMovies && (
                        <div className="grid gap-6 grid-cols-1 lg:grid-cols-2 mt-6">
                            {microMovies.map((m) => (
                                <div key={m.id} className="bg-slate-50 p-6 rounded-xl shadow-sm border border-slate-200">
                                    <h3 className="font-bold text-lg mb-2 text-purple-900">Avatar: {m.generation_metadata?.avatar_type || 'Custom'}</h3>
                                    <div className="prose prose-sm"><pre className="whitespace-pre-wrap font-sans text-gray-700">{m.content}</pre></div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
