import { useCallback } from 'react';
import { useAuth } from '../context/AuthContext';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
const API_URL = `${API_BASE}/research`;

async function handleResponse(response) {
    if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Request failed (${response.status})`);
    }
    return response.json();
}

export function useResearchApi() {
    const { authFetch } = useAuth();

    const searchAndSave = useCallback(async (request) => {
        const response = await authFetch(`${API_URL}/search-and-save`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(request)
        });
        return handleResponse(response);
    }, [authFetch]);

    const getSavedSearches = useCallback(async () => {
        const response = await authFetch(`${API_URL}/saved-searches`);
        return handleResponse(response);
    }, [authFetch]);

    const getSavedSearch = useCallback(async (searchId) => {
        const response = await authFetch(`${API_URL}/saved-searches/${searchId}`);
        return handleResponse(response);
    }, [authFetch]);

    const deleteSavedSearch = useCallback(async (searchId) => {
        const response = await authFetch(`${API_URL}/saved-searches/${searchId}`, { method: 'DELETE' });
        return handleResponse(response);
    }, [authFetch]);

    const getApiUsage = useCallback(async () => {
        const response = await authFetch(`${API_URL}/api-usage`);
        return handleResponse(response);
    }, [authFetch]);

    const getBlacklist = useCallback(async () => {
        const response = await authFetch(`${API_URL}/blacklist`);
        return handleResponse(response);
    }, [authFetch]);

    const addToBlacklist = useCallback(async (pageName, reason = null) => {
        const params = new URLSearchParams({ page_name: pageName });
        if (reason) params.append('reason', reason);
        const response = await authFetch(`${API_URL}/blacklist?${params}`, { method: 'POST' });
        return handleResponse(response);
    }, [authFetch]);

    const removeFromBlacklist = useCallback(async (blacklistId) => {
        const response = await authFetch(`${API_URL}/blacklist/${blacklistId}`, { method: 'DELETE' });
        return handleResponse(response);
    }, [authFetch]);

    const getKeywordBlacklist = useCallback(async () => {
        const response = await authFetch(`${API_URL}/keyword-blacklist`);
        return handleResponse(response);
    }, [authFetch]);

    const addToKeywordBlacklist = useCallback(async (keyword, reason = null) => {
        const params = new URLSearchParams({ keyword });
        if (reason) params.append('reason', reason);
        const response = await authFetch(`${API_URL}/keyword-blacklist?${params}`, { method: 'POST' });
        return handleResponse(response);
    }, [authFetch]);

    const removeFromKeywordBlacklist = useCallback(async (blacklistId) => {
        const response = await authFetch(`${API_URL}/keyword-blacklist/${blacklistId}`, { method: 'DELETE' });
        return handleResponse(response);
    }, [authFetch]);

    const getRateLimit = useCallback(async () => {
        const response = await authFetch(`${API_URL}/rate-limit`);
        return handleResponse(response);
    }, [authFetch]);

    const getFacebookPages = useCallback(async (limit = 50, offset = 0, sortBy = 'total_ads') => {
        const params = new URLSearchParams({ limit, offset, sort_by: sortBy });
        const response = await authFetch(`${API_URL}/facebook-pages?${params}`);
        return handleResponse(response);
    }, [authFetch]);

    const getVerticals = useCallback(async () => {
        const response = await authFetch(`${API_URL}/verticals`);
        return handleResponse(response);
    }, [authFetch]);

    const createVertical = useCallback(async (name, description = null) => {
        const params = new URLSearchParams({ name });
        if (description) params.append('description', description);
        const response = await authFetch(`${API_URL}/verticals?${params}`, { method: 'POST' });
        return handleResponse(response);
    }, [authFetch]);

    const getVerticalAggregatedAds = useCallback(async (verticalId) => {
        const response = await authFetch(`${API_URL}/verticals/${verticalId}/aggregated-ads`);
        return handleResponse(response);
    }, [authFetch]);

    const getVerticalPageAds = useCallback(async (verticalId, pageId) => {
        const response = await authFetch(`${API_URL}/verticals/${verticalId}/pages/${pageId}/ads`);
        return handleResponse(response);
    }, [authFetch]);

    const createBrandScrape = useCallback(async (brandName, pageUrl) => {
        const response = await authFetch(`${API_URL}/brand-scrapes`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ brand_name: brandName, page_url: pageUrl })
        });
        return handleResponse(response);
    }, [authFetch]);

    const getBrandScrapes = useCallback(async () => {
        const response = await authFetch(`${API_URL}/brand-scrapes`);
        return handleResponse(response);
    }, [authFetch]);

    const getBrandScrape = useCallback(async (scrapeId) => {
        const response = await authFetch(`${API_URL}/brand-scrapes/${scrapeId}`);
        return handleResponse(response);
    }, [authFetch]);

    const deleteBrandScrape = useCallback(async (scrapeId) => {
        const response = await authFetch(`${API_URL}/brand-scrapes/${scrapeId}`, { method: 'DELETE' });
        return handleResponse(response);
    }, [authFetch]);

    return {
        searchAndSave, getSavedSearches, getSavedSearch, deleteSavedSearch,
        getApiUsage, getBlacklist, addToBlacklist, removeFromBlacklist,
        getKeywordBlacklist, addToKeywordBlacklist, removeFromKeywordBlacklist,
        getRateLimit, getFacebookPages, getVerticals, createVertical,
        getVerticalAggregatedAds, getVerticalPageAds,
        createBrandScrape, getBrandScrapes, getBrandScrape, deleteBrandScrape
    };
}
