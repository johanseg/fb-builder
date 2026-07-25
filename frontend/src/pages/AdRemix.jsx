import React, { useMemo, useState } from 'react';
import { ChevronLeft, Sparkles, Check, Image, FileText, Users } from 'lucide-react';
import { useBrands } from '../context/BrandContext';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import ImageTemplateSelector from '../components/ImageTemplateSelector';
import ProfileSelectionStep from '../components/steps/ProfileSelectionStep';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function AdRemix() {
    const { activeBrand, customerProfiles } = useBrands();
    const { showError } = useToast();
    const { authFetch } = useAuth();
    const [currentStep, setCurrentStep] = useState(1);
    const [loading, setLoading] = useState(false);
    const [adConcept, setAdConcept] = useState(null);

    const [wizardData, setWizardData] = useState({
        template: null,
        profile: null,
        campaignDetails: {
            offer: '',
            urgency: '',
            messaging: ''
        }
    });

    const effectiveWizardData = useMemo(() => ({
        ...wizardData,
        brand: activeBrand,
        product: activeBrand?.products?.[0] || null,
    }), [wizardData, activeBrand]);

    const steps = [
        { id: 1, name: 'Template', icon: Image },
        { id: 2, name: 'Profile', icon: Users },
        { id: 3, name: 'Campaign', icon: FileText },
        { id: 4, name: 'Review', icon: Check }
    ];

    const updateData = (field, value) => {
        setWizardData(prev => ({ ...prev, [field]: value }));
    };

    const updateCampaignDetails = (field, value) => {
        setWizardData(prev => ({
            ...prev,
            campaignDetails: { ...prev.campaignDetails, [field]: value }
        }));
    };

    const handleReconstruct = async () => {
        setLoading(true);
        try {
            const response = await authFetch(`${API_URL}/ad-remix/reconstruct`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    template_id: effectiveWizardData.template.id,
                    brand_id: effectiveWizardData.brand.id,
                    product_id: effectiveWizardData.product.id,
                    profile_id: effectiveWizardData.profile.id,
                    campaign_offer: effectiveWizardData.campaignDetails.offer,
                    campaign_urgency: effectiveWizardData.campaignDetails.urgency,
                    campaign_messaging: effectiveWizardData.campaignDetails.messaging
                })
            });

            if (!response.ok) throw new Error('Reconstruction failed');

            const data = await response.json();
            setAdConcept(data);
            setCurrentStep(5); // Move to results step
        } catch (error) {
            console.error('Reconstruction error:', error);
            showError('Failed to reconstruct ad. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleTemplateSelect = async (template) => {
        setLoading(true);
        try {
            const response = await authFetch(`${API_URL}/ad-remix/deconstruct`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ template_id: template.id }),
            });
            if (!response.ok) throw new Error('Template analysis failed');
            updateData('template', template);
            setCurrentStep(2);
        } catch (error) {
            console.error('Template analysis error:', error);
            showError('Failed to analyze the selected template. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-5xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground flex items-center gap-3">
                    <Sparkles size={32} className="text-purple-600" />
                    Ad Remix Engine
                </h1>
                <p className="text-muted-foreground mt-1">Deconstruct winning ads and reconstruct them with your brand</p>
            </div>

            {/* Progress Steps */}
            <div className="mb-8 bg-card rounded-xl shadow-sm border border-border p-6">
                <div className="flex items-center justify-between relative">
                    <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-full h-1 bg-muted -z-10"></div>
                    {steps.map((step) => {
                        const Icon = step.icon;
                        const isActive = step.id === currentStep;
                        const isCompleted = step.id < currentStep;

                        return (
                            <div
                                key={step.id}
                                className="flex flex-col items-center bg-card px-2"
                            >
                                <div
                                    className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-all ${isActive ? 'bg-purple-600 text-white scale-110 shadow-md' :
                                        isCompleted ? 'bg-green-500 text-white' :
                                            'bg-muted text-muted-foreground'
                                        }`}
                                >
                                    {isCompleted ? <Check size={20} /> : <Icon size={20} />}
                                </div>
                                <span className={`text-xs font-medium ${isActive ? 'text-purple-600' : 'text-muted-foreground'}`}>
                                    {step.name}
                                </span>
                            </div>
                        );
                    })}</div>
            </div>

            {/* Step Content */}
            <div className="bg-card rounded-xl shadow-sm border border-border p-8 min-h-[500px]">
                {loading && (
                    <div className="absolute inset-0 bg-card/80 backdrop-blur-sm z-50 flex flex-col items-center justify-center rounded-xl">
                        <div className="w-16 h-16 border-4 border-purple-200 border-t-purple-600 rounded-full animate-spin mb-4"></div>
                        <h3 className="text-xl font-bold text-foreground">
                            {currentStep === 1 ? 'Analyzing Template Structure...' : 'Generating Your Ad Concept...'}
                        </h3>
                    </div>
                )}

                {/* Step 1: Template Selection */}
                {currentStep === 1 && (
                    <div>
                        <h3 className="text-xl font-bold mb-4">Select a Winning Template to Remix</h3>
                        <p className="text-muted-foreground mb-6">Choose an ad template to deconstruct and use as your blueprint</p>
                        <ImageTemplateSelector
                            onSelect={handleTemplateSelect}
                            onClose={() => { }}
                            embedded={true}
                        />
                    </div>
                )}

                {/* Step 2: Profile Selection */}
                {currentStep === 2 && (
                    <ProfileSelectionStep
                        profiles={customerProfiles}
                        selectedProfile={effectiveWizardData.profile}
                        onSelect={(profile) => {
                            updateData('profile', profile);
                            setCurrentStep(3);
                        }}
                    />
                )}

                {/* Step 3: Campaign Details */}
                {currentStep === 3 && (
                    <div>
                        <h3 className="text-xl font-bold mb-4">Campaign Details</h3>
                        <p className="text-muted-foreground mb-6">Provide details to customize your remixed ad</p>

                        <div className="max-w-2xl space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-2">
                                    Offer / Promotion *
                                </label>
                                <input
                                    type="text"
                                    value={effectiveWizardData.campaignDetails.offer}
                                    onChange={(e) => updateCampaignDetails('offer', e.target.value)}
                                    placeholder="e.g., 50% off Black Friday, Buy 2 Get 1 Free"
                                    className="w-full px-4 py-3 border border-border rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-foreground mb-2">
                                    Urgency / Timing
                                </label>
                                <input
                                    type="text"
                                    value={effectiveWizardData.campaignDetails.urgency}
                                    onChange={(e) => updateCampaignDetails('urgency', e.target.value)}
                                    placeholder="e.g., Limited time, Ends tonight"
                                    className="w-full px-4 py-3 border border-border rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-foreground mb-2">
                                    Key Messaging *
                                </label>
                                <textarea
                                    value={effectiveWizardData.campaignDetails.messaging}
                                    onChange={(e) => updateCampaignDetails('messaging', e.target.value)}
                                    placeholder="e.g., Science-backed results, Trusted by 10,000+ customers"
                                    rows={3}
                                    className="w-full px-4 py-3 border border-border rounded-lg focus:ring-2 focus:ring-purple-600 focus:border-transparent"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 4: Review & Generate */}
                {currentStep === 4 && (
                    <div>
                        <h3 className="text-xl font-bold mb-4">Review & Generate</h3>
                        <p className="text-muted-foreground mb-6">Review your selections and generate the remixed ad concept</p>

                        <div className="space-y-4 max-w-2xl">
                            <div className="bg-secondary p-4 rounded-lg">
                                <h4 className="font-bold text-foreground mb-2">Template</h4>
                                <p className="text-foreground">{effectiveWizardData.template?.name}</p>
                            </div>

                            <div className="bg-secondary p-4 rounded-lg">
                                <h4 className="font-bold text-foreground mb-2">Brand</h4>
                                <p className="text-foreground">{effectiveWizardData.brand?.name}</p>
                            </div>

                            <div className="bg-secondary p-4 rounded-lg">
                                <h4 className="font-bold text-foreground mb-2">Product</h4>
                                <p className="text-foreground">{effectiveWizardData.product?.name}</p>
                            </div>

                            <div className="bg-secondary p-4 rounded-lg">
                                <h4 className="font-bold text-foreground mb-2">Audience</h4>
                                <p className="text-foreground">{effectiveWizardData.profile?.name}</p>
                            </div>

                            <div className="bg-secondary p-4 rounded-lg">
                                <h4 className="font-bold text-foreground mb-2">Campaign</h4>
                                <p className="text-foreground"><strong>Offer:</strong> {effectiveWizardData.campaignDetails.offer}</p>
                                {effectiveWizardData.campaignDetails.urgency && (
                                    <p className="text-foreground"><strong>Urgency:</strong> {effectiveWizardData.campaignDetails.urgency}</p>
                                )}
                                <p className="text-foreground"><strong>Messaging:</strong> {effectiveWizardData.campaignDetails.messaging}</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Step 5: Results */}
                {currentStep === 5 && adConcept && (
                    <div>
                        <div className="text-center mb-8">
                            <div className="w-20 h-20 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Check size={40} />
                            </div>
                            <h2 className="text-3xl font-bold text-foreground mb-2">Ad Concept Generated!</h2>
                            <p className="text-muted-foreground">Your remixed ad concept is ready</p>
                        </div>

                        <div className="space-y-6 max-w-3xl mx-auto">
                            <div className="bg-purple-50 border-2 border-purple-200 rounded-xl p-6">
                                <h4 className="font-bold text-purple-900 mb-3 flex items-center gap-2">
                                    <FileText size={20} />
                                    Headline
                                </h4>
                                <p className="text-lg font-bold text-foreground">{adConcept.headline_remix}</p>
                            </div>

                            <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-6">
                                <h4 className="font-bold text-blue-900 mb-3">Body Copy</h4>
                                <p className="text-foreground whitespace-pre-line">{adConcept.body_copy}</p>
                            </div>

                            <div className="bg-green-50 border-2 border-green-200 rounded-xl p-6">
                                <h4 className="font-bold text-green-900 mb-3">Call to Action</h4>
                                <button className="px-6 py-3 bg-green-600 text-white rounded-lg font-bold">
                                    {adConcept.cta_button}
                                </button>
                            </div>

                            <div className="bg-amber-50 border-2 border-amber-200 rounded-xl p-6">
                                <h4 className="font-bold text-foreground mb-3 flex items-center gap-2">
                                    <Image size={20} />
                                    Visual Description
                                </h4>
                                <p className="text-foreground">{adConcept.visual_description}</p>
                            </div>

                            <div className="bg-secondary border-2 border-border rounded-xl p-6">
                                <h4 className="font-bold text-foreground mb-3 flex items-center gap-2">
                                    <Sparkles size={20} />
                                    Image Generation Prompt
                                </h4>
                                <p className="text-sm text-foreground font-mono bg-card p-4 rounded border border-border">
                                    {adConcept.image_generation_prompt}
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>

            {/* Navigation */}
            <div className="mt-6 flex items-center justify-between">
                <div></div>
                <div className="flex gap-3">
                    {currentStep > 1 && currentStep < 5 && (
                        <button
                            onClick={() => setCurrentStep(currentStep - 1)}
                            className="flex items-center gap-2 px-6 py-3 bg-secondary text-foreground rounded-lg hover:bg-muted font-medium"
                        >
                            <ChevronLeft size={20} />
                            Back
                        </button>
                    )}

                    {currentStep === 4 && (
                        <button
                            onClick={handleReconstruct}
                            disabled={!effectiveWizardData.campaignDetails.offer || !effectiveWizardData.campaignDetails.messaging}
                            className="flex items-center gap-2 px-8 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg hover:from-purple-700 hover:to-pink-700 font-medium shadow-lg disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            <Sparkles size={20} />
                            Generate Remix
                        </button>
                    )}

                    {currentStep === 5 && (
                        <button
                            onClick={() => window.location.reload()}
                            className="px-6 py-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 font-medium"
                        >
                            Create Another Remix
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
