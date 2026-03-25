import React, { useState, useEffect } from 'react';
import { ChevronRight, Check, Wand2, Layout, Image as ImageIcon, BarChart2, Layers } from 'lucide-react';
import CopyBuilder from './CopyBuilder';
import TemplateSelector from './TemplateSelector';
import AnalyzeTemplatesStep from './AnalyzeTemplatesStep';
import NanoBananaGenerationStep from './NanoBananaGenerationStep';
import BulkAdCreation from './BulkAdCreation';
import { useBrands } from '../context/BrandContext';
import { useCampaign } from '../context/CampaignContext';
import { useToast } from '../context/ToastContext';

const Wizard = () => {
    const { showSuccess } = useToast();
    const [step, setStep] = useState(1);
    const { brands, activeBrand, setActiveBrand } = useBrands();
    const { setCreativeData } = useCampaign();

    // Wizard State
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [selectedTemplate, setSelectedTemplate] = useState(null);
    const [copyData, setCopyData] = useState({
        productName: '',
        targetAudience: '',
        generatedCopy: '',
        headline: '',
        cta: ''
    });

    // Auto-select brand and product from context
    useEffect(() => {
        if (brands.length > 0 && !activeBrand) {
            setActiveBrand(brands[0]);
        }
    }, [brands, activeBrand, setActiveBrand]);

    // Auto-select first product when brand becomes available
    useEffect(() => {
        if (activeBrand?.products?.length > 0 && !selectedProduct) {
            const product = activeBrand.products[0];
            setSelectedProduct(product); // eslint-disable-line react-hooks/set-state-in-effect
            setCopyData(prev => ({ ...prev, productName: product.name }));
        }
    }, [activeBrand]); // eslint-disable-line react-hooks/exhaustive-deps

    const handleNext = () => {
        setStep(step + 1);
    };

    const handleBack = () => {
        setStep(step - 1);
    };

    const handleImagesGenerated = (images) => {
        // Update global creative data for BulkAdCreation
        setCreativeData(prev => ({
            ...prev,
            creatives: images.map(img => ({
                id: img.id,
                file: null, // No file object for generated images yet
                previewUrl: img.previewUrl,
                imageUrl: img.url,
                name: img.name
            })),
            headlines: [copyData.headline],
            bodies: [copyData.generatedCopy],
            cta: copyData.cta || 'LEARN_MORE',
            creativeName: `${activeBrand.name} - ${selectedProduct.name} Batch`
        }));
    };

    const steps = [
        { id: 1, name: 'Choose Template', icon: Layout },
        { id: 2, name: 'Analyze', icon: BarChart2 },
        { id: 3, name: 'Copy Builder', icon: Wand2 },
        { id: 4, name: 'Generate', icon: ImageIcon },
        { id: 5, name: 'Create Batch', icon: Layers },
    ];

    return (
        <div className="max-w-6xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-foreground">Video Ad Builder</h1>
                <p className="text-muted-foreground mt-1">Create video ads with AI-generated content</p>
            </div>

            {/* Progress Bar */}
            <div className="mb-10">
                <div className="flex items-center justify-between relative">
                    <div className="absolute left-0 top-1/2 transform -translate-y-1/2 w-full h-1 bg-muted -z-10"></div>
                    {steps.map((s) => {
                        const Icon = s.icon;
                        const isActive = s.id === step;
                        const isCompleted = s.id < step;

                        return (
                            <div key={s.id} className="flex flex-col items-center bg-secondary px-2">
                                <div
                                    className={`w-10 h-10 rounded-full flex items-center justify-center mb-2 transition-colors ${isActive ? 'bg-blue-600 text-white' :
                                        isCompleted ? 'bg-green-500 text-white' : 'bg-muted text-muted-foreground'
                                        }`}
                                >
                                    {isCompleted ? <Check size={20} /> : <Icon size={20} />}
                                </div>
                                <span className={`text-xs font-medium hidden md:block ${isActive ? 'text-blue-600' : 'text-muted-foreground'}`}>
                                    {s.name}
                                </span>
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Step Content */}
            <div className="bg-card rounded-2xl shadow-sm border border-border p-8 min-h-[500px]">

                {/* Step 1: Template Selection */}
                {step === 1 && (
                    <TemplateSelector
                        selectedTemplate={selectedTemplate}
                        onSelect={setSelectedTemplate}
                        onNext={handleNext}
                        onBack={handleBack}
                    />
                )}

                {/* Step 2: Analyze Templates */}
                {step === 2 && (
                    <AnalyzeTemplatesStep
                        selectedTemplate={selectedTemplate}
                        onNext={handleNext}
                        onBack={handleBack}
                    />
                )}

                {/* Step 3: Copy Builder */}
                {step === 3 && (
                    <CopyBuilder
                        data={copyData}
                        setData={setCopyData}
                        onNext={handleNext}
                        brandVoice={activeBrand?.voice}
                        activeBrand={activeBrand}
                    />
                )}

                {/* Step 4: Generate Images (Nano Banana Pro) */}
                {step === 4 && (
                    <NanoBananaGenerationStep
                        copyData={copyData}
                        selectedTemplate={selectedTemplate}
                        onImagesGenerated={handleImagesGenerated}
                        onNext={handleNext}
                        onBack={handleBack}
                    />
                )}

                {/* Step 5: Create Batch */}
                {step === 5 && (
                    <BulkAdCreation
                        onNext={() => showSuccess('Campaign Created Successfully!')}
                        onBack={handleBack}
                    />
                )}
            </div>
        </div>
    );
};

export default Wizard;
