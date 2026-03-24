import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileImage, Video, ArrowRight, Grid3X3 } from 'lucide-react';

export default function CreateAds() {
    const navigate = useNavigate();

    return (
        <div className="max-w-5xl mx-auto">
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground">Create New Ad</h1>
                <p className="text-muted-foreground mt-2">Select the format you want to create</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                {/* Image Ad Card */}
                <button
                    onClick={() => navigate('/image-ads')}
                    className="group relative flex flex-col items-start p-8 bg-card rounded-2xl border-2 border-border hover:border-amber-200 hover:shadow-xl transition-all duration-300 text-left"
                >
                    <div className="w-16 h-16 bg-amber-100 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                        <FileImage size={32} className="text-amber-600" />
                    </div>

                    <h3 className="text-2xl font-bold text-foreground mb-3">Image Ad</h3>
                    <p className="text-muted-foreground mb-8 leading-relaxed">
                        Create high-converting static image ads using our template library or AI generation. Perfect for feed posts and stories.
                    </p>

                    <div className="mt-auto flex items-center gap-2 text-amber-600 font-semibold group-hover:gap-3 transition-all">
                        Start Creating <ArrowRight size={20} />
                    </div>
                </button>

                {/* Video Ad Card */}
                <button
                    onClick={() => navigate('/video-ads')}
                    className="group relative flex flex-col items-start p-8 bg-card rounded-2xl border-2 border-border hover:border-blue-200 hover:shadow-xl transition-all duration-300 text-left"
                >
                    <div className="w-16 h-16 bg-blue-100 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                        <Video size={32} className="text-blue-600" />
                    </div>

                    <h3 className="text-2xl font-bold text-foreground mb-3">Video Ad</h3>
                    <p className="text-muted-foreground mb-8 leading-relaxed">
                        Generate engaging video ads from product shots or stock footage. Ideal for Reels, Stories, and TikTok.
                    </p>

                    <div className="mt-auto flex items-center gap-2 text-blue-600 font-semibold group-hover:gap-3 transition-all">
                        Start Creating <ArrowRight size={20} />
                    </div>
                </button>

                {/* Modular Ads Card */}
                <button
                    onClick={() => navigate('/modular-ads')}
                    className="group relative flex flex-col items-start p-8 bg-card rounded-2xl border-2 border-border hover:border-purple-200 hover:shadow-xl transition-all duration-300 text-left md:col-span-2"
                >
                    <div className="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform duration-300">
                        <Grid3X3 size={32} className="text-purple-600" />
                    </div>

                    <h3 className="text-2xl font-bold text-foreground mb-3">Modular Script Matrix <span className="text-xs ml-2 bg-purple-100 text-purple-600 px-2 py-1 rounded-full uppercase tracking-wider font-semibold">New Workflow</span></h3>
                    <p className="text-muted-foreground mb-8 leading-relaxed max-w-2xl">
                        Generate a 1,800+ variation testing matrix using the Inceptly Modular Creative System. Create specialized Intros, Bridges, Cores, and CTAs driven by your Product Knowledge Base.
                    </p>

                    <div className="mt-auto flex items-center gap-2 text-purple-600 font-semibold group-hover:gap-3 transition-all">
                        Launch Factory <ArrowRight size={20} />
                    </div>
                </button>
            </div>
        </div>
    );
}
