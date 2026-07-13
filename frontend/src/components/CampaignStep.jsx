import React, { useCallback, useEffect, useState } from 'react';
import { ChevronRight, ChevronLeft, Check, Loader, Plus, LayoutTemplate, Trash2 } from 'lucide-react';
import { useCampaign } from '../context/CampaignContext';
import { useToast } from '../context/ToastContext';
import { getCampaigns, getCampaignTemplates, deleteCampaignTemplate } from '../lib/facebookApi';

const CAMPAIGN_OBJECTIVES = [
    { value: 'OUTCOME_SALES', label: 'Sales - Drive purchases and conversions' },
    { value: 'OUTCOME_TRAFFIC', label: 'Traffic - Send people to your website' },
    { value: 'OUTCOME_LEADS', label: 'Leads - Collect leads for your business' },
    { value: 'OUTCOME_ENGAGEMENT', label: 'Engagement - Get more messages, video views, etc.' },
    { value: 'OUTCOME_AWARENESS', label: 'Awareness - Reach people near your business' },
    { value: 'OUTCOME_APP_PROMOTION', label: 'App Promotion - Get more app installs' }
];

const BID_STRATEGIES = [
    { value: 'LOWEST_COST_WITHOUT_CAP', label: 'Lowest Cost (Highest Volume or Value, No Cap)' },
    { value: 'LOWEST_COST_WITH_BID_CAP', label: 'Lowest Cost with Bid Cap' },
    { value: 'COST_CAP', label: 'Cost Cap (Cost Per Result Goal)' }
];

const CampaignStep = ({ onNext, onBack }) => {
    const { campaignData, setCampaignData, setAdsetData, setCreativeData, selectedAdAccount } = useCampaign();
    const { showError, showWarning, showSuccess } = useToast();
    const [mode, setMode] = useState('new'); // 'new' or 'existing'
    const [templates, setTemplates] = useState([]);

    useEffect(() => {
        getCampaignTemplates()
            .then(setTemplates)
            .catch(err => console.error('Error loading templates:', err));
    }, []);

    const applyTemplate = (template) => {
        const config = template.config || {};
        if (config.campaign) {
            setCampaignData(prev => ({ ...prev, ...config.campaign, id: null, fbCampaignId: null, isExisting: false }));
        }
        if (config.adset) {
            setAdsetData(prev => ({ ...prev, ...config.adset, id: null, fbAdsetId: null, isExisting: false }));
        }
        setCreativeData(prev => ({
            ...prev,
            ...(config.description != null ? { description: config.description } : {}),
            ...(config.cta ? { cta: config.cta } : {}),
            ...(config.website_url ? { websiteUrl: config.website_url } : {}),
        }));
        setMode('new');
        showSuccess(`Template "${template.name}" applied`);
    };

    const handleDeleteTemplate = async (template, e) => {
        e.stopPropagation();
        try {
            await deleteCampaignTemplate(template.id);
            setTemplates(prev => prev.filter(t => t.id !== template.id));
        } catch (err) {
            showError(`Failed to delete template: ${err.message}`);
        }
    };
    const [existingCampaigns, setExistingCampaigns] = useState([]);
    const [selectedCampaign, setSelectedCampaign] = useState(null);
    const [loadingCampaigns, setLoadingCampaigns] = useState(false);

    const fetchExistingCampaigns = useCallback(async () => {
        if (!selectedAdAccount) return;

        setLoadingCampaigns(true);
        try {
            const campaigns = await getCampaigns(selectedAdAccount.id);
            setExistingCampaigns(campaigns);
        } catch (error) {
            console.error('Error fetching campaigns:', error);
            showError(`Error fetching campaigns: ${error.message}`);
        } finally {
            setLoadingCampaigns(false);
        }
    }, [selectedAdAccount, showError]);

    useEffect(() => {
        // Fetch campaigns when switching to existing mode
        if (mode === 'existing' && selectedAdAccount) {
            fetchExistingCampaigns();
        }
    }, [mode, selectedAdAccount, fetchExistingCampaigns]);

    const handleSelectExisting = (campaign) => {
        setSelectedCampaign(campaign);

        const dailyBudget = campaign.dailyBudget ? parseInt(campaign.dailyBudget) / 100 : 0;
        const lifetimeBudget = campaign.lifetimeBudget ? parseInt(campaign.lifetimeBudget) / 100 : 0;

        // CBO campaigns have budget set at campaign level
        // ABO campaigns have budget set at ad set level (campaign budget is 0 or null)
        const isCBO = dailyBudget > 0 || lifetimeBudget > 0;

        setCampaignData({
            ...campaign,
            budgetType: isCBO ? 'CBO' : 'ABO',
            dailyBudget: dailyBudget,
            bidStrategy: campaign.bid_strategy || '',
            fbCampaignId: campaign.id,
            isExisting: true
        });
    };

    const handleInputChange = (field, value) => {
        setCampaignData(prev => ({
            ...prev,
            [field]: value,
            isExisting: false
        }));
    };

    const handleNext = async () => {
        if (mode === 'existing' && !selectedCampaign) {
            showWarning('Please select a campaign');
            return;
        }

        if (mode === 'existing') {
            // For existing campaigns, we just use the selected data
            // No need to call API or create anything new
            // The data is already set in handleSelectExisting
        }

        if (mode === 'new') {
            if (!campaignData.name || !campaignData.objective) {
                showWarning('Please fill in all required fields');
                return;
            }

            if (campaignData.budgetType === 'CBO' && (!campaignData.dailyBudget || campaignData.dailyBudget <= 0)) {
                showWarning('Please enter a valid Daily Budget for CBO campaign');
                return;
            }

            // Validate Bid Amount if strategy requires it (for CBO campaigns)
            if (campaignData.budgetType === 'CBO' &&
                (campaignData.bidStrategy === 'LOWEST_COST_WITH_BID_CAP' || campaignData.bidStrategy === 'COST_CAP') &&
                (!campaignData.bidAmount || campaignData.bidAmount <= 0)) {
                showWarning('Please enter a valid Bid Amount for the selected bid strategy');
                return;
            }

            // For new campaigns, we just prepare the data
            // The actual creation happens in the final step (BulkAdCreation)
            const id = `camp_${Date.now()}`;
            setCampaignData(prev => ({ ...prev, id }));
        }

        onNext();
    };

    return (
        <div>
            <h2 className="text-2xl font-bold mb-6">Campaign Setup</h2>

            {/* Templates */}
            {templates.length > 0 && (
                <div className="mb-6">
                    <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground mb-2">
                        <LayoutTemplate size={16} /> Start from a template
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {templates.map(template => (
                            <button
                                key={template.id}
                                onClick={() => applyTemplate(template)}
                                className="group flex items-center gap-2 px-3 py-1.5 bg-secondary border border-border rounded-full text-sm text-foreground hover:border-amber-500 hover:bg-amber-50 transition-colors"
                            >
                                {template.name}
                                <Trash2
                                    size={13}
                                    className="text-muted-foreground opacity-0 group-hover:opacity-100 hover:text-red-500"
                                    onClick={(e) => handleDeleteTemplate(template, e)}
                                />
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Mode Toggle */}
            <div className="flex gap-4 mb-6">
                <button
                    onClick={() => {
                        setMode('new');
                        setCampaignData(prev => ({
                            ...prev,
                            isExisting: false,
                            fbCampaignId: null
                        }));
                    }}
                    className={`flex-1 p-4 rounded-xl border-2 transition-all ${mode === 'new'
                        ? 'border-amber-600 bg-amber-50'
                        : 'border-border hover:border-amber-300'
                        }`}
                >
                    <Plus className="mx-auto mb-2" size={24} />
                    <div className="font-semibold">Create New Campaign</div>
                </button>
                <button
                    onClick={() => setMode('existing')}
                    className={`flex-1 p-4 rounded-xl border-2 transition-all ${mode === 'existing'
                        ? 'border-amber-600 bg-amber-50'
                        : 'border-border hover:border-amber-300'
                        }`}
                >
                    <Check className="mx-auto mb-2" size={24} />
                    <div className="font-semibold">Use Existing Campaign</div>
                </button>
            </div>

            {/* Existing Campaigns List */}
            {mode === 'existing' && (
                <div className="space-y-4 mb-6">
                    {/* Existing Campaigns */}
                    <div>
                        <h3 className="font-semibold text-foreground mb-3">Select a Campaign</h3>
                        {loadingCampaigns ? (
                            <div className="flex items-center justify-center gap-2 text-muted-foreground py-8">
                                <Loader className="animate-spin" size={20} />
                                <span>Loading campaigns from Facebook...</span>
                            </div>
                        ) : existingCampaigns.length === 0 ? (
                            <p className="text-muted-foreground text-center py-8">No campaigns found in this ad account.</p>
                        ) : (
                            existingCampaigns.map(campaign => (
                                <div
                                    key={campaign.id}
                                    onClick={() => handleSelectExisting(campaign)}
                                    className={`p-4 rounded-xl border-2 cursor-pointer transition-all mb-2 ${selectedCampaign?.id === campaign.id
                                        ? 'border-amber-600 bg-amber-50'
                                        : 'border-border hover:border-amber-300'
                                        }`}
                                >
                                    <div className="flex justify-between items-start">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2">
                                                <div className="font-bold text-foreground">{campaign.name}</div>
                                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${campaign.status === 'ACTIVE' ? 'bg-green-100 text-green-700' :
                                                    campaign.status === 'PAUSED' ? 'bg-yellow-100 text-yellow-700' :
                                                        'bg-secondary text-foreground'
                                                    }`}>
                                                    {campaign.status}
                                                </span>
                                            </div>
                                            <div className="text-sm text-muted-foreground mt-1">
                                                <span className="font-medium text-foreground">
                                                    {(campaign.dailyBudget || campaign.lifetimeBudget) ? 'CBO' : 'ABO'}
                                                </span>
                                                {' • '}{campaign.objective}
                                                {campaign.dailyBudget && ` • Daily: $${(parseInt(campaign.dailyBudget) / 100).toFixed(2)}`}
                                                {campaign.lifetimeBudget && ` • Lifetime: $${(parseInt(campaign.lifetimeBudget) / 100).toFixed(2)}`}
                                            </div>
                                        </div>
                                        {selectedCampaign?.id === campaign.id && (
                                            <Check className="text-amber-600" size={20} />
                                        )}
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                </div>
            )}

            {/* New Campaign Form */}
            {mode === 'new' && (
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-foreground mb-2">
                            Campaign Name *
                        </label>
                        <input
                            type="text"
                            value={campaignData.name}
                            onChange={(e) => handleInputChange('name', e.target.value)}
                            placeholder="Summer Sale Campaign"
                            className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-2">
                            Campaign Objective *
                        </label>
                        <select
                            value={campaignData.objective}
                            onChange={(e) => handleInputChange('objective', e.target.value)}
                            className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                        >
                            <option value="">Select objective...</option>
                            {CAMPAIGN_OBJECTIVES.map(obj => (
                                <option key={obj.value} value={obj.value}>{obj.label}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-foreground mb-2">
                            Budget Type *
                        </label>
                        <div className="grid grid-cols-2 gap-4">
                            <button
                                type="button"
                                onClick={() => handleInputChange('budgetType', 'ABO')}
                                className={`p-3 rounded-lg border-2 transition-all ${campaignData.budgetType === 'ABO'
                                    ? 'border-amber-600 bg-amber-50'
                                    : 'border-border hover:border-amber-300'
                                    }`}
                            >
                                <div className="font-semibold">ABO</div>
                                <div className="text-xs text-muted-foreground">Ad Set Budget</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => handleInputChange('budgetType', 'CBO')}
                                className={`p-3 rounded-lg border-2 transition-all ${campaignData.budgetType === 'CBO'
                                    ? 'border-amber-600 bg-amber-50'
                                    : 'border-border hover:border-amber-300'
                                    }`}
                            >
                                <div className="font-semibold">CBO</div>
                                <div className="text-xs text-muted-foreground">Campaign Budget</div>
                            </button>
                        </div>
                    </div>

                    {campaignData.budgetType === 'CBO' && (
                        <>
                            <div>
                                <label className="block text-sm font-medium text-foreground mb-2">
                                    Daily Budget (USD)
                                </label>
                                <div className="relative">
                                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                        <span className="text-muted-foreground">$</span>
                                    </div>
                                    <input
                                        type="number"
                                        value={campaignData.dailyBudget || ''}
                                        onChange={(e) => handleInputChange('dailyBudget', parseInt(e.target.value) || 0)}
                                        placeholder="100"
                                        min="1"
                                        step="1"
                                        className="w-full pl-7 pr-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                    />
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-foreground mb-2">
                                    Bid Strategy
                                </label>
                                <select
                                    value={campaignData.bidStrategy}
                                    onChange={(e) => handleInputChange('bidStrategy', e.target.value)}
                                    className="w-full px-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                >
                                    <option value="">Select bid strategy...</option>
                                    {BID_STRATEGIES.map(strategy => (
                                        <option key={strategy.value} value={strategy.value}>{strategy.label}</option>
                                    ))}
                                </select>
                            </div>

                            {/* Bid Amount - Required for Cost Cap and Bid Cap strategies */}
                            {(campaignData.bidStrategy === 'COST_CAP' || campaignData.bidStrategy === 'LOWEST_COST_WITH_BID_CAP') && (
                                <div>
                                    <label className="block text-sm font-medium text-foreground mb-2">
                                        {campaignData.bidStrategy === 'COST_CAP' ? 'Cost Cap Amount (USD)' : 'Bid Cap Amount (USD)'} *
                                    </label>
                                    <div className="relative">
                                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                                            <span className="text-muted-foreground">$</span>
                                        </div>
                                        <input
                                            type="number"
                                            value={campaignData.bidAmount || ''}
                                            onChange={(e) => handleInputChange('bidAmount', parseFloat(e.target.value) || 0)}
                                            placeholder="10.00"
                                            min="0.01"
                                            step="0.01"
                                            className="w-full pl-7 pr-4 py-2 border border-border rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                        />
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1">
                                        {campaignData.bidStrategy === 'COST_CAP'
                                            ? 'Maximum average cost per result you want to maintain'
                                            : 'Maximum bid amount for each auction'}
                                    </p>
                                </div>
                            )}
                        </>
                    )}
                </div>
            )}

            {/* Navigation */}
            <div className="mt-8 flex justify-between">
                {onBack && (
                    <button
                        onClick={onBack}
                        className="px-6 py-3 text-muted-foreground hover:text-foreground font-medium"
                    >
                        Back
                    </button>
                )}
                <button
                    onClick={handleNext}
                    disabled={loadingCampaigns}
                    className="ml-auto flex items-center gap-2 px-6 py-3 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
                >
                    {loadingCampaigns ? 'Loading...' : 'Next Step'} <ChevronRight size={20} />
                </button>
            </div>
        </div>
    );
};

export default CampaignStep;
