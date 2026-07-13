import React, { createContext, useContext, useState } from 'react';

const CampaignContext = createContext();

export const useCampaign = () => {
    const context = useContext(CampaignContext);
    if (!context) {
        throw new Error('useCampaign must be used within CampaignProvider');
    }
    return context;
};

// Helper to compute default start time (tomorrow at 1:00 AM local)
const getDefaultStartTime = () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    tomorrow.setHours(1, 0, 0, 0);
    const year = tomorrow.getFullYear();
    const month = String(tomorrow.getMonth() + 1).padStart(2, '0');
    const day = String(tomorrow.getDate()).padStart(2, '0');
    const hours = String(tomorrow.getHours()).padStart(2, '0');
    const minutes = String(tomorrow.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
};

const DEFAULT_CAMPAIGN = {
    id: null,
    name: '',
    objective: 'OUTCOME_SALES',
    budgetType: 'ABO',
    dailyBudget: 0,
    bidStrategy: '',
    status: 'PAUSED',
    fbCampaignId: null,
    isExisting: false,
};

const DEFAULT_ADSET = {
    id: null,
    name: '',
    optimizationGoal: 'OFFSITE_CONVERSIONS',
    dailyBudget: 0,
    bidStrategy: 'LOWEST_COST_WITHOUT_CAP',
    bidAmount: 0,
    targeting: {
        genders: [], // [] = All, [1] = Male, [2] = Female
        publisher_platforms: ['facebook', 'instagram'], // Default to Manual (FB & IG)
        geo_locations: {
            countries: ['US'],
            excluded_countries: [],
            regions: [],
            excluded_regions: [],
            cities: [],
            excluded_cities: [],
            geo_markets: [],
            excluded_geo_markets: [],
        },
        ageMin: 18,
        ageMax: 65,
    },
    advantageAudience: 0, // 0 = Off, 1 = On
    startTime: null, // set dynamically below
    pixelId: '',
    conversionEvent: 'PURCHASE',
    attributionSetting: '7d_click', // Default to 7-day click attribution
    status: 'PAUSED',
    fbAdsetId: null,
    isExisting: false,
};

const DEFAULT_CREATIVE = {
    creativeName: '',
    creatives: [], // Array of { id, file, previewUrl, name }
    bodies: [''], // Start with 1 field
    headlines: [''], // Start with 1 field
    description: '',
    cta: 'LEARN_MORE',
    websiteUrl: '',
    pageId: '',
    instagramId: null, // Explicitly set to null when no IG account is connected
};

export const CampaignProvider = ({ children }) => {
    const [campaignData, setCampaignData] = useState({ ...DEFAULT_CAMPAIGN });
    const [adsetData, setAdsetData] = useState({ ...DEFAULT_ADSET, startTime: getDefaultStartTime() });
    const [creativeData, setCreativeData] = useState({ ...DEFAULT_CREATIVE });
    const [adsData, setAdsData] = useState([]);
    const [selectedAdAccount, setSelectedAdAccount] = useState(null);
    // Additional accounts to replicate the launch into (multi-account launch)
    const [extraAdAccounts, setExtraAdAccounts] = useState([]);
    const [launchStatus, setLaunchStatus] = useState('PAUSED');

    const resetWizard = () => {
        setCampaignData({ ...DEFAULT_CAMPAIGN });
        setAdsetData({ ...DEFAULT_ADSET, startTime: getDefaultStartTime() });
        setCreativeData({ ...DEFAULT_CREATIVE });
        setAdsData([]);
        setSelectedAdAccount(null);
        setExtraAdAccounts([]);
        setLaunchStatus('PAUSED');
    };

    const value = {
        campaignData,
        setCampaignData,
        adsetData,
        setAdsetData,
        creativeData,
        setCreativeData,
        adsData,
        setAdsData,
        selectedAdAccount,
        setSelectedAdAccount,
        extraAdAccounts,
        setExtraAdAccounts,
        launchStatus,
        setLaunchStatus,
        resetWizard
    };

    return (
        <CampaignContext.Provider value={value}>
            {children}
        </CampaignContext.Provider>
    );
};
