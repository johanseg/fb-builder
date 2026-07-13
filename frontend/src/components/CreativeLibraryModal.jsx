import React, { useEffect, useMemo, useState } from 'react';
import { X, Search, Film, Image, Loader, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

/**
 * Modal to pick creatives from the GeneratedAds library and add them to the
 * launch wizard without re-uploading (their URLs are already remote-hosted).
 * Render conditionally ({open && <CreativeLibraryModal/>}) so state resets per open.
 */
const CreativeLibraryModal = ({ onClose, onSelect }) => {
    const { authFetch } = useAuth();
    const [ads, setAds] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedIds, setSelectedIds] = useState(new Set());
    const [importCopy, setImportCopy] = useState(false);

    useEffect(() => {
        let cancelled = false;
        authFetch(`${API_URL}/generated-ads`)
            .then(res => {
                if (!res.ok) throw new Error(`Failed to load library (${res.status})`);
                return res.json();
            })
            .then(data => {
                if (!cancelled) setAds(Array.isArray(data) ? data : []);
            })
            .catch(err => {
                if (!cancelled) setError(err.message);
            })
            .finally(() => {
                if (!cancelled) setLoading(false);
            });
        return () => { cancelled = true; };
    }, [authFetch]);

    const filteredAds = useMemo(() => {
        const term = searchTerm.toLowerCase();
        return ads.filter(ad =>
            term === '' ||
            (ad.headline?.toLowerCase() || '').includes(term) ||
            (ad.body?.toLowerCase() || '').includes(term)
        );
    }, [ads, searchTerm]);

    const toggleAd = (adId) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(adId)) next.delete(adId);
            else next.add(adId);
            return next;
        });
    };

    const handleAdd = () => {
        const selected = ads.filter(ad => selectedIds.has(ad.id));
        onSelect(selected, { importCopy });
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
            <div className="bg-background border border-border rounded-xl shadow-xl w-full max-w-4xl max-h-[85vh] flex flex-col">
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-border">
                    <h3 className="text-lg font-semibold">Pick Creatives from Library</h3>
                    <button onClick={onClose} className="p-1 text-muted-foreground hover:text-foreground" title="Close">
                        <X size={20} />
                    </button>
                </div>

                {/* Search */}
                <div className="p-4 border-b border-border">
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
                        <input
                            type="text"
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            placeholder="Search by headline or body..."
                            className="w-full pl-9 pr-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent text-sm"
                        />
                    </div>
                </div>

                {/* Grid */}
                <div className="flex-1 overflow-y-auto p-4">
                    {loading ? (
                        <div className="flex items-center justify-center py-12 gap-2 text-muted-foreground">
                            <Loader className="animate-spin" size={20} />
                            <span>Loading library...</span>
                        </div>
                    ) : error ? (
                        <p className="text-center text-red-500 py-12">{error}</p>
                    ) : filteredAds.length === 0 ? (
                        <p className="text-center text-muted-foreground py-12">
                            {ads.length === 0 ? 'No generated creatives yet. Create some in Image Ads or Video Ads first.' : 'No creatives match your search.'}
                        </p>
                    ) : (
                        <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                            {filteredAds.map(ad => {
                                const isSelected = selectedIds.has(ad.id);
                                const previewUrl = ad.media_type === 'video' ? (ad.thumbnail_url || ad.video_url) : ad.image_url;
                                return (
                                    <button
                                        key={ad.id}
                                        onClick={() => toggleAd(ad.id)}
                                        className={`relative group border-2 rounded-lg overflow-hidden aspect-square bg-secondary text-left ${isSelected ? 'border-amber-500 ring-2 ring-amber-300' : 'border-transparent hover:border-amber-400'}`}
                                    >
                                        {previewUrl ? (
                                            <img src={previewUrl} alt={ad.headline || 'Creative'} className="w-full h-full object-cover" loading="lazy" />
                                        ) : (
                                            <div className="w-full h-full flex items-center justify-center text-muted-foreground">
                                                <Film size={24} />
                                            </div>
                                        )}
                                        <div className="absolute top-1.5 left-1.5">
                                            {ad.media_type === 'video' ? (
                                                <span className="bg-purple-600 text-white text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1"><Film size={10} /> Video</span>
                                            ) : (
                                                <span className="bg-blue-600 text-white text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1"><Image size={10} /> Image</span>
                                            )}
                                        </div>
                                        {isSelected && (
                                            <div className="absolute top-1.5 right-1.5 text-amber-500 bg-white rounded-full">
                                                <CheckCircle2 size={20} />
                                            </div>
                                        )}
                                        {ad.headline && (
                                            <div className="absolute bottom-0 left-0 right-0 bg-black/60 text-white text-[10px] p-1 truncate">
                                                {ad.headline}
                                            </div>
                                        )}
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between p-4 border-t border-border">
                    <label className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
                        <input
                            type="checkbox"
                            checked={importCopy}
                            onChange={(e) => setImportCopy(e.target.checked)}
                            className="rounded border-border text-amber-600 focus:ring-amber-500"
                        />
                        Also import headline &amp; body text
                    </label>
                    <div className="flex gap-2">
                        <button onClick={onClose} className="px-4 py-2 text-muted-foreground hover:text-foreground font-medium text-sm">
                            Cancel
                        </button>
                        <button
                            onClick={handleAdd}
                            disabled={selectedIds.size === 0}
                            className="px-4 py-2 bg-amber-600 text-white rounded-lg font-medium text-sm hover:bg-amber-700 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Add {selectedIds.size > 0 ? selectedIds.size : ''} Creative{selectedIds.size !== 1 ? 's' : ''}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CreativeLibraryModal;
