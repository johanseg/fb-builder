import React, { useState } from 'react';
import { X, Smartphone } from 'lucide-react';

export default function SafeZonePreview({ content, onClose }) {
    const [platform, setPlatform] = useState('tiktok');

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-[60]">
            <div className="bg-gray-900 rounded-3xl flex flex-col items-center p-6 shadow-2xl border border-gray-800 relative max-w-sm w-full">
                <button 
                    onClick={onClose}
                    className="absolute -top-4 -right-4 bg-card text-foreground p-2 rounded-full hover:bg-muted transition-colors"
                >
                    <X size={20} />
                </button>

                <div className="flex items-center gap-3 mb-6 w-full px-4 text-white">
                    <Smartphone size={24} className="text-purple-400" />
                    <h3 className="text-lg font-bold">Safe Zone Checker</h3>
                </div>

                {/* 9:16 Phone Frame */}
                <div className="relative w-[300px] h-[533px] bg-slate-800 rounded-3xl overflow-hidden border-8 border-gray-950 shadow-inner">
                    
                    {/* Content Layer */}
                    <div className="absolute inset-0 p-6 pt-16 pb-24 overflow-y-auto custom-scrollbar">
                        <div className="font-sans text-white text-sm leading-relaxed whitespace-pre-wrap">
                            {content}
                        </div>
                    </div>

                    {/* TikTok Overlay Simulator */}
                    {platform === 'tiktok' && (
                        <div className="pointer-events-none absolute inset-0 text-white z-10">
                            {/* Top UI Area */}
                            <div className="absolute top-0 left-0 right-0 h-16 bg-gradient-to-b from-black/60 to-transparent flex items-start justify-center pt-2 gap-4 text-xs font-bold opacity-70">
                                <span>Following</span>
                                <span className="underline decoration-2 underline-offset-4">For You</span>
                            </div>

                            {/* Right Action Buttons Area */}
                            <div className="absolute right-2 bottom-20 w-12 flex flex-col gap-4 items-center opacity-80">
                                {[...Array(5)].map((_, i) => (
                                    <div key={i} className="w-10 h-10 bg-card/20 backdrop-blur-sm rounded-full flex flex-col items-center justify-center border border-white/10 shadow-sm">
                                    </div>
                                ))}
                            </div>

                            {/* Bottom Caption Area */}
                            <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black/80 via-black/40 to-transparent p-4 flex flex-col justify-end">
                                <div className="w-32 h-3 bg-card/20 rounded-full mb-2"></div>
                                <div className="w-48 h-2 bg-card/20 rounded-full mb-1"></div>
                                <div className="w-40 h-2 bg-card/20 rounded-full"></div>
                            </div>
                        </div>
                    )}

                    {/* Reels Overlay Simulator */}
                    {platform === 'reels' && (
                        <div className="pointer-events-none absolute inset-0 text-white z-10">
                            {/* Top UI */}
                            <div className="absolute top-4 left-4 font-bold text-lg opacity-80">Reels</div>
                            <div className="absolute top-4 right-4 w-6 h-6 bg-card/20 rounded-full"></div>

                            {/* Right Action Buttons Area */}
                            <div className="absolute right-2 bottom-16 w-12 flex flex-col gap-5 items-center opacity-80">
                                {[...Array(4)].map((_, i) => (
                                    <div key={i} className="w-8 h-8 bg-transparent border-2 border-white/60 rounded-full"></div>
                                ))}
                            </div>

                            {/* Bottom Caption Area */}
                            <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-black/70 to-transparent p-4 flex flex-col justify-end">
                                <div className="w-24 h-4 bg-card/20 rounded-full mb-3 flex items-center gap-2">
                                    <div className="w-4 h-4 rounded-full bg-card/40 ml-1"></div>
                                    <div className="w-12 h-2 bg-card/40 rounded-full"></div>
                                </div>
                                <div className="w-full h-2 bg-card/20 rounded-full"></div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Platform Toggles */}
                <div className="flex gap-2 mt-6 w-full">
                    <button 
                        onClick={() => setPlatform('tiktok')}
                        className={`flex-1 py-2 text-sm font-bold rounded-xl transition-all ${platform === 'tiktok' ? 'bg-[#00f2fe] text-foreground border-none' : 'bg-gray-800 text-muted-foreground hover:bg-gray-700'}`}
                    >
                        TikTok UI
                    </button>
                    <button 
                        onClick={() => setPlatform('reels')}
                        className={`flex-1 py-2 text-sm font-bold rounded-xl transition-all ${platform === 'reels' ? 'bg-gradient-to-tr from-[#f09433] via-[#e6683c] to-[#bc1888] text-white' : 'bg-gray-800 text-muted-foreground hover:bg-gray-700'}`}
                    >
                        IG Reels UI
                    </button>
                </div>
            </div>
        </div>
    );
}
