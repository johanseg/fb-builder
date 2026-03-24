import React, { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { useBrands } from '../context/BrandContext';
import { Plus, Edit2, Trash2, Loader, UserCircle2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function AIPersonas() {
    const { authFetch } = useAuth();
    const { showError, showSuccess } = useToast();
    const { activeBrand } = useBrands();

    const [personas, setPersonas] = useState([]);
    const [loading, setLoading] = useState(true);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingPersona, setEditingPersona] = useState(null);
    const [saving, setSaving] = useState(false);
    const [deleteTarget, setDeleteTarget] = useState(null);
    const [formData, setFormData] = useState({
        name: '',
        description: '',
        voice_guidelines: '',
        base_image_url: ''
    });

    useEffect(() => {
        if (activeBrand) {
            fetchPersonas();
        } else {
            setPersonas([]);
            setLoading(false);
        }
    }, [activeBrand]);

    const fetchPersonas = async () => {
        setLoading(true);
        try {
            const res = await authFetch(`${API_URL}/personas/?brand_id=${activeBrand.id}`);
            if (!res.ok) throw new Error('Failed to load personas');
            const data = await res.json();
            setPersonas(data);
        } catch (err) {
            showError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            const url = editingPersona 
                ? `${API_URL}/personas/${editingPersona.id}`
                : `${API_URL}/personas/`;
            const method = editingPersona ? 'PUT' : 'POST';
            
            const payload = { ...formData };
            if (!editingPersona) payload.brand_id = activeBrand.id;

            const res = await authFetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const doc = await res.json();
                throw new Error(doc.detail || 'Save failed');
            }

            showSuccess(`Persona ${editingPersona ? 'updated' : 'created'}`);
            setIsModalOpen(false);
            fetchPersonas();
        } catch(err) {
            showError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDelete = async (id) => {
        try {
            const res = await authFetch(`${API_URL}/personas/${id}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Delete failed');
            showSuccess('Persona deleted');
            setDeleteTarget(null);
            fetchPersonas();
        } catch(err) {
            showError(err.message);
        }
    };

    const openCreate = () => {
        setEditingPersona(null);
        setFormData({ name: '', description: '', voice_guidelines: '', base_image_url: '' });
        setIsModalOpen(true);
    };

    const openEdit = (p) => {
        setEditingPersona(p);
        setFormData({
            name: p.name || '',
            description: p.description || '',
            voice_guidelines: p.voice_guidelines || '',
            base_image_url: p.base_image_url || ''
        });
        setIsModalOpen(true);
    };

    if (!activeBrand) {
        return <div className="p-8 text-center text-muted-foreground">Please select a brand to manage AI Personas.</div>;
    }

    return (
        <div className="max-w-6xl mx-auto space-y-6">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
                        <UserCircle2 className="text-purple-600" /> AI Personas
                    </h1>
                    <p className="text-muted-foreground text-sm mt-1">Manage virtual actors, creators, and voices for micro-movie generation.</p>
                </div>
                <button onClick={openCreate} className="px-4 py-2 bg-purple-600 text-white rounded-lg flex items-center gap-2 font-bold hover:bg-purple-700">
                    <Plus size={18} /> New Persona
                </button>
            </div>

            {loading ? (
                <div className="flex justify-center py-12"><Loader className="animate-spin text-purple-600" size={32} /></div>
            ) : personas.length === 0 ? (
                <div className="bg-card rounded-2xl border border-border p-12 text-center">
                    <UserCircle2 className="mx-auto text-gray-300 mb-4" size={48} />
                    <h3 className="text-lg font-bold text-foreground mb-2">No personas found</h3>
                    <p className="text-muted-foreground">Create an AI Persona to use dynamically in script generation.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {personas.map(p => (
                        <div key={p.id} className="bg-card rounded-2xl border border-border shadow-sm p-5 hover:shadow-md transition-shadow relative group">
                            <div className="absolute top-4 right-4 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button onClick={() => openEdit(p)} className="p-1.5 text-muted-foreground hover:text-purple-600 bg-secondary rounded-lg hover:bg-purple-50"><Edit2 size={16} /></button>
                                <button onClick={() => setDeleteTarget(p)} className="p-1.5 text-muted-foreground hover:text-red-600 bg-secondary rounded-lg hover:bg-red-50"><Trash2 size={16} /></button>
                            </div>
                            
                            <div className="flex items-center gap-4 mb-4">
                                {p.base_image_url ? (
                                    <img src={p.base_image_url} alt={p.name} className="w-14 h-14 rounded-full object-cover border-2 border-purple-100" />
                                ) : (
                                    <div className="w-14 h-14 rounded-full bg-purple-100 flex items-center justify-center text-purple-600 font-bold text-xl">
                                        {p.name.charAt(0)}
                                    </div>
                                )}
                                <div>
                                    <h3 className="font-bold text-foreground">{p.name}</h3>
                                    <p className="text-xs text-muted-foreground line-clamp-1">{p.description}</p>
                                </div>
                            </div>
                            
                            <div className="space-y-3 mt-4 pt-4 border-t border-border">
                                <div>
                                    <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-1">Voice Guidelines</p>
                                    <p className="text-sm text-foreground line-clamp-3 bg-secondary p-2 rounded-lg">{p.voice_guidelines || 'No voice instructions given.'}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {deleteTarget && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-card rounded-2xl p-6 shadow-2xl max-w-sm w-full">
                        <h2 className="text-lg font-bold text-foreground mb-2">Delete Persona</h2>
                        <p className="text-sm text-muted-foreground mb-6">Are you sure you want to delete <strong>{deleteTarget.name}</strong>? This cannot be undone.</p>
                        <div className="flex justify-end gap-3">
                            <button onClick={() => setDeleteTarget(null)} className="px-4 py-2 bg-secondary text-foreground font-bold rounded-xl hover:bg-muted">Cancel</button>
                            <button onClick={() => handleDelete(deleteTarget.id)} className="px-4 py-2 bg-red-600 text-white font-bold rounded-xl hover:bg-red-700">Delete</button>
                        </div>
                    </div>
                </div>
            )}

            {isModalOpen && (
                <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
                    <form onSubmit={handleSave} className="bg-card rounded-2xl p-6 shadow-2xl max-w-lg w-full">
                        <h2 className="text-xl font-bold mb-6">{editingPersona ? 'Edit Persona' : 'Create Persona'}</h2>
                        
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-bold text-foreground mb-1">Name</label>
                                <input required type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full p-2.5 border border-border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none" placeholder="e.g. The Overwhelmed Mom" />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-foreground mb-1">Description</label>
                                <textarea value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} className="w-full p-2.5 border border-border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none min-h-[80px]" placeholder="Who is this character?" />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-foreground mb-1">Voice Guidelines</label>
                                <textarea value={formData.voice_guidelines} onChange={e => setFormData({...formData, voice_guidelines: e.target.value})} className="w-full p-2.5 border border-border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none min-h-[100px]" placeholder="Specific instructions for the LLM when writing for this persona (e.g. Uses GenZ slang, highly enthusiastic, skeptical tone...)" />
                            </div>
                            <div>
                                <label className="block text-sm font-bold text-foreground mb-1">Avatar Image URL (Optional)</label>
                                <input type="text" value={formData.base_image_url} onChange={e => setFormData({...formData, base_image_url: e.target.value})} className="w-full p-2.5 border border-border rounded-lg focus:ring-2 focus:ring-purple-500 outline-none text-sm" placeholder="https://..." />
                            </div>
                        </div>

                        <div className="mt-8 flex justify-end gap-3">
                            <button type="button" onClick={() => setIsModalOpen(false)} className="px-4 py-2 bg-secondary text-foreground font-bold rounded-xl hover:bg-muted">Cancel</button>
                            <button type="submit" disabled={saving} className="px-6 py-2 bg-purple-600 text-white font-bold rounded-xl hover:bg-purple-700 flex items-center gap-2">
                                {saving ? <Loader className="animate-spin" size={18}/> : null}
                                Save Persona
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
}
