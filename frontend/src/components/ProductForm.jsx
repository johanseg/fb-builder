import React, { useState, useRef } from 'react';
import { X, Upload, Loader, ChevronDown, ChevronUp } from 'lucide-react';
import { useBrands } from '../context/BrandContext';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { validateProductName, validateProductDescription } from '../utils/validation';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const ProductForm = ({ onClose, onSave, initialData = null }) => {
    const { brands } = useBrands();
    const { showSuccess, showError } = useToast();
    const { authFetch } = useAuth();
    const [formData, setFormData] = useState({
        name: initialData?.name || '',
        description: initialData?.description || '',
        brandId: initialData?.brandId || '',
        product_shots: initialData?.product_shots || [],
        pain_points: (initialData?.pain_points || []).join('\n'),
        desired_outcomes: (initialData?.desired_outcomes || []).join('\n'),
        root_causes: (initialData?.root_causes || []).join('\n'),
        proof_points: (initialData?.proof_points || []).join('\n'),
        differentiators: (initialData?.differentiators || []).join('\n'),
        risk_reversals: (initialData?.risk_reversals || []).join('\n')
    });
    const [showBrief, setShowBrief] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [saving, setSaving] = useState(false);
    const fileInputRef = useRef(null);

    // Client-side validation constants
    const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
    const MAX_SIZE = 10 * 1024 * 1024; // 10MB

    const handleSubmit = async (e) => {
        e.preventDefault();
        setSaving(true);
        try {
            if (!formData.brandId) {
                throw new Error('Please select a brand');
            }

            const validatedData = {
                ...formData,
                name: validateProductName(formData.name),
                description: validateProductDescription(formData.description),
                product_shots: formData.product_shots || [],
                pain_points: formData.pain_points ? formData.pain_points.split('\n').map(s => s.trim()).filter(Boolean) : [],
                desired_outcomes: formData.desired_outcomes ? formData.desired_outcomes.split('\n').map(s => s.trim()).filter(Boolean) : [],
                root_causes: formData.root_causes ? formData.root_causes.split('\n').map(s => s.trim()).filter(Boolean) : [],
                proof_points: formData.proof_points ? formData.proof_points.split('\n').map(s => s.trim()).filter(Boolean) : [],
                differentiators: formData.differentiators ? formData.differentiators.split('\n').map(s => s.trim()).filter(Boolean) : [],
                risk_reversals: formData.risk_reversals ? formData.risk_reversals.split('\n').map(s => s.trim()).filter(Boolean) : []
            };

            await onSave(validatedData);
            showSuccess('Product saved successfully');
            onClose();
        } catch (err) {
            showError(err.message);
        } finally {
            setSaving(false);
        }
    };

    const handleFileUpload = async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;

        // Client-side validation
        for (const file of files) {
            if (!ALLOWED_TYPES.includes(file.type)) {
                showError(`Invalid file type: ${file.name}. Allowed types: JPEG, PNG, GIF, WebP`);
                return;
            }
            if (file.size > MAX_SIZE) {
                showError(`File too large: ${file.name}. Maximum size: 10MB`);
                return;
            }
        }

        setUploading(true);
        try {
            const newShots = [];
            for (const file of files) {
                const uploadData = new FormData();
                uploadData.append('file', file);

                const response = await authFetch(`${API_URL}/uploads/`, {
                    method: 'POST',
                    body: uploadData
                });

                if (!response.ok) {
                    const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
                    throw new Error(errorData.detail || 'Upload failed');
                }

                const data = await response.json();
                newShots.push(data.url);
            }

            setFormData(prev => ({
                ...prev,
                product_shots: [...(prev.product_shots || []), ...newShots]
            }));
            showSuccess(`Successfully uploaded ${newShots.length} image(s)`);
        } catch (err) {
            console.error('Upload error:', err);
            showError(err.message || 'Failed to upload images');
        } finally {
            setUploading(false);
            if (fileInputRef.current) fileInputRef.current.value = '';
        }
    };

    const removeShot = (index) => {
        setFormData(prev => ({
            ...prev,
            product_shots: prev.product_shots.filter((_, i) => i !== index)
        }));
    };

    return (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4" onClick={onClose}>
            <div className="bg-card rounded-xl shadow-xl w-full max-w-md max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
                <div className="flex justify-between items-center p-6 border-b border-border">
                    <h2 className="text-xl font-bold text-foreground">
                        {initialData ? 'Edit Product' : 'Add New Product'}
                    </h2>
                    <button onClick={onClose} className="text-muted-foreground hover:bg-secondary p-2 rounded-full">
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1">Brand</label>
                        <select
                            required
                            value={formData.brandId}
                            onChange={e => setFormData({ ...formData, brandId: e.target.value })}
                            className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500"
                            disabled={!!initialData}
                        >
                            <option value="">Select a Brand...</option>
                            {brands.map(brand => (
                                <option key={brand.id} value={brand.id}>{brand.name}</option>
                            ))}
                        </select>
                        {brands.length === 0 && (
                            <p className="text-xs text-red-500 mt-1">No brands available. Please create a brand first.</p>
                        )}
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1">Product Name</label>
                        <input
                            required
                            type="text"
                            maxLength={100}
                            value={formData.name}
                            onChange={e => setFormData({ ...formData, name: e.target.value })}
                            className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500"
                            placeholder="e.g. Glow Serum"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-1">Description</label>
                        <textarea
                            value={formData.description}
                            maxLength={500}
                            onChange={e => setFormData({ ...formData, description: e.target.value })}
                            className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500"
                            rows="3"
                            placeholder="Short description of the product..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-2">Product Shots</label>
                        <div className="grid grid-cols-3 gap-2 mb-3">
                            {(formData.product_shots || []).map((shot, index) => (
                                <div key={index} className="relative aspect-square bg-secondary rounded-lg overflow-hidden group">
                                    <img src={shot} alt={`Product shot ${index + 1}`} className="w-full h-full object-cover" />
                                    <button
                                        type="button"
                                        onClick={() => removeShot(index)}
                                        className="absolute top-1 right-1 bg-red-500 text-white p-1 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                                    >
                                        <X size={12} />
                                    </button>
                                </div>
                            ))}
                            <button
                                type="button"
                                onClick={() => fileInputRef.current?.click()}
                                disabled={uploading}
                                className="aspect-square border-2 border-dashed border-border rounded-lg flex flex-col items-center justify-center text-muted-foreground hover:border-blue-500 hover:text-blue-500 transition-colors"
                            >
                                {uploading ? <Loader size={20} className="animate-spin" /> : <Upload size={20} />}
                                <span className="text-xs mt-1">{uploading ? 'Uploading...' : 'Upload'}</span>
                            </button>
                        </div>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            multiple
                            onChange={handleFileUpload}
                            className="hidden"
                        />
                        <p className="text-xs text-muted-foreground">Upload product images to use in ad generation.</p>
                    </div>

                    {/* Creative Brief Settings (Collapsible) */}
                    <div className="border border-border rounded-lg overflow-hidden">
                        <button
                            type="button"
                            onClick={() => setShowBrief(!showBrief)}
                            className="w-full flex items-center justify-between p-4 bg-secondary hover:bg-secondary transition-colors"
                        >
                            <div>
                                <h3 className="font-semibold text-foreground text-left">Product Knowledge Base (Creative Brief)</h3>
                                <p className="text-sm text-muted-foreground text-left">Information used by the AI to generate ad scripts</p>
                            </div>
                            {showBrief ? <ChevronUp size={20} className="text-muted-foreground" /> : <ChevronDown size={20} className="text-muted-foreground" />}
                        </button>
                        
                        {showBrief && (
                            <div className="p-4 bg-card space-y-4 border-t border-border max-h-[400px] overflow-y-auto">
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-1">Primary Pain Points (1 per line)</label>
                                    <textarea
                                        value={formData.pain_points}
                                        onChange={e => setFormData({ ...formData, pain_points: e.target.value })}
                                        className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                        rows="3"
                                        placeholder="E.g. Wasting hours manually editing videos\nAds fatigue too quickly in the Meta algorithm"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-1">Desired Outcomes (1 per line)</label>
                                    <textarea
                                        value={formData.desired_outcomes}
                                        onChange={e => setFormData({ ...formData, desired_outcomes: e.target.value })}
                                        className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                        rows="3"
                                        placeholder="E.g. Scale ad spend profitably\nGet endless fresh creative variations automatically"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-1">Root Causes / Mechanisms (1 per line)</label>
                                    <textarea
                                        value={formData.root_causes}
                                        onChange={e => setFormData({ ...formData, root_causes: e.target.value })}
                                        className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                        rows="3"
                                        placeholder="E.g. Platform changes require high creative volume but production is slow"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-1">Proof Points (1 per line)</label>
                                    <textarea
                                        value={formData.proof_points}
                                        onChange={e => setFormData({ ...formData, proof_points: e.target.value })}
                                        className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                        rows="3"
                                        placeholder="E.g. Trusted by 5,000+ top D2C brands\nGenerated over $1B in tracked revenue"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-1">Differentiators (1 per line)</label>
                                    <textarea
                                        value={formData.differentiators}
                                        onChange={e => setFormData({ ...formData, differentiators: e.target.value })}
                                        className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                        rows="3"
                                        placeholder="E.g. Proprietary modular AI generation vs standard templatized tools"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-1">Risk Reversals (1 per line)</label>
                                    <textarea
                                        value={formData.risk_reversals}
                                        onChange={e => setFormData({ ...formData, risk_reversals: e.target.value })}
                                        className="w-full p-2 border border-border rounded-lg focus:ring-2 focus:ring-blue-500 text-sm"
                                        rows="2"
                                        placeholder="E.g. 14-day free trial\nCancel anytime"
                                    />
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="flex justify-end gap-3 pt-4 border-t border-border">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 text-foreground hover:bg-secondary rounded-lg"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={saving || uploading}
                            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {saving && <Loader size={16} className="animate-spin" />}
                            {saving ? 'Saving...' : 'Save Product'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ProductForm;
