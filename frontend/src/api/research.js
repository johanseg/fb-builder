import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const API_URL = `${API_BASE}/research`;

const getAuthHeaders = () => {
    const token = localStorage.getItem('accessToken');
    return {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
    };
};

export const searchAndSave = async (request) => {
    try {
        const response = await axios.post(`${API_URL}/search-and-save`, request, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error searching and saving:', error);
        throw error;
    }
};

export const getSavedSearches = async () => {
    try {
        const response = await axios.get(`${API_URL}/saved-searches`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching saved searches:', error);
        throw error;
    }
};

export const getSavedSearch = async (searchId) => {
    try {
        const response = await axios.get(`${API_URL}/saved-searches/${searchId}`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching saved search:', error);
        throw error;
    }
};

export const deleteSavedSearch = async (searchId) => {
    try {
        const response = await axios.delete(`${API_URL}/saved-searches/${searchId}`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error deleting saved search:', error);
        throw error;
    }
};

export const getApiUsage = async () => {
    try {
        const response = await axios.get(`${API_URL}/api-usage`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching API usage:', error);
        throw error;
    }
};

export const getBlacklist = async () => {
    try {
        const response = await axios.get(`${API_URL}/blacklist`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching blacklist:', error);
        throw error;
    }
};

export const addToBlacklist = async (pageName, reason = null) => {
    try {
        const response = await axios.post(`${API_URL}/blacklist`, null, {
            headers: getAuthHeaders(),
            params: { page_name: pageName, reason }
        });
        return response.data;
    } catch (error) {
        console.error('Error adding to blacklist:', error);
        throw error;
    }
};

export const removeFromBlacklist = async (blacklistId) => {
    try {
        const response = await axios.delete(`${API_URL}/blacklist/${blacklistId}`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error removing from blacklist:', error);
        throw error;
    }
};

export const getKeywordBlacklist = async () => {
    try {
        const response = await axios.get(`${API_URL}/keyword-blacklist`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching keyword blacklist:', error);
        throw error;
    }
};

export const addToKeywordBlacklist = async (keyword, reason = null) => {
    try {
        const response = await axios.post(`${API_URL}/keyword-blacklist`, null, {
            headers: getAuthHeaders(),
            params: { keyword, reason }
        });
        return response.data;
    } catch (error) {
        console.error('Error adding to keyword blacklist:', error);
        throw error;
    }
};

export const removeFromKeywordBlacklist = async (blacklistId) => {
    try {
        const response = await axios.delete(`${API_URL}/keyword-blacklist/${blacklistId}`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error removing from keyword blacklist:', error);
        throw error;
    }
};

export const getRateLimit = async () => {
    try {
        const response = await axios.get(`${API_URL}/rate-limit`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching rate limit:', error);
        throw error;
    }
};

export const getFacebookPages = async (limit = 50, offset = 0, sortBy = 'total_ads') => {
    try {
        const response = await axios.get(`${API_URL}/facebook-pages`, {
            headers: getAuthHeaders(),
            params: { limit, offset, sort_by: sortBy }
        });
        return response.data;
    } catch (error) {
        console.error('Error fetching Facebook pages:', error);
        throw error;
    }
};

export const getVerticals = async () => {
    try {
        const response = await axios.get(`${API_URL}/verticals`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching verticals:', error);
        throw error;
    }
};

export const createVertical = async (name, description = null) => {
    try {
        const response = await axios.post(`${API_URL}/verticals`, null, {
            headers: getAuthHeaders(),
            params: { name, description }
        });
        return response.data;
    } catch (error) {
        console.error('Error creating vertical:', error);
        throw error;
    }
};

export const getVerticalAggregatedAds = async (verticalId) => {
    try {
        const response = await axios.get(`${API_URL}/verticals/${verticalId}/aggregated-ads`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching vertical aggregated ads:', error);
        throw error;
    }
};

export const getVerticalPageAds = async (verticalId, pageId) => {
    try {
        const response = await axios.get(`${API_URL}/verticals/${verticalId}/pages/${pageId}/ads`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching vertical page ads:', error);
        throw error;
    }
};

// Brand Scrapes API
export const createBrandScrape = async (brandName, pageUrl) => {
    try {
        const response = await axios.post(`${API_URL}/brand-scrapes`, {
            brand_name: brandName,
            page_url: pageUrl
        }, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error creating brand scrape:', error);
        throw error;
    }
};

export const getBrandScrapes = async () => {
    try {
        const response = await axios.get(`${API_URL}/brand-scrapes`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching brand scrapes:', error);
        throw error;
    }
};

export const getBrandScrape = async (scrapeId) => {
    try {
        const response = await axios.get(`${API_URL}/brand-scrapes/${scrapeId}`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error fetching brand scrape:', error);
        throw error;
    }
};

export const deleteBrandScrape = async (scrapeId) => {
    try {
        const response = await axios.delete(`${API_URL}/brand-scrapes/${scrapeId}`, { headers: getAuthHeaders() });
        return response.data;
    } catch (error) {
        console.error('Error deleting brand scrape:', error);
        throw error;
    }
};
