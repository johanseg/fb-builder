// Facebook Marketing API Integration Service
// Now proxies through our backend with authentication

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1') + '/facebook';

/**
 * Get all ad accounts accessible by the access token
 */
export async function getAdAccounts(authFetch) {
    try {
        const response = await authFetch(`${API_BASE_URL}/accounts`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch ad accounts');
        }
        const accounts = await response.json();

        // Map backend response to frontend expected format if necessary
        // Backend returns raw FB data list
        return accounts.map(account => ({
            id: account.id,
            accountId: account.account_id,
            name: account.name,
            status: account.account_status,
            currency: account.currency,
            timezone: account.timezone_name,
            balance: account.balance,
            amountSpent: account.amount_spent,
            spendCap: account.spend_cap,
            businessName: account.business_name,
            fundingSource: account.funding_source_details,
            minDailyBudget: account.min_daily_budget,
            age: account.age,
            disableReason: account.disable_reason
        }));
    } catch (error) {
        console.error('Error fetching ad accounts:', error);
        throw error;
    }
}

/**
 * Get all campaigns for a specific ad account
 */
export async function getCampaigns(adAccountId, authFetch) {
    try {
        // Backend service currently fetches all campaigns for the connected account
        // It doesn't filter by adAccountId in the service call yet, but assumes the env var account
        // For now, we'll just call the endpoint
        const response = await authFetch(`${API_BASE_URL}/campaigns?ad_account_id=${adAccountId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch campaigns');
        }
        const campaigns = await response.json();

        return campaigns.map(campaign => ({
            id: campaign.id,
            name: campaign.name,
            objective: campaign.objective,
            status: campaign.status,
            dailyBudget: campaign.daily_budget,
            lifetimeBudget: campaign.lifetime_budget,
            budgetRemaining: campaign.budget_remaining,
            createdTime: campaign.created_time,
            updatedTime: campaign.updated_time,
            isCBO: campaign.is_adset_budget_sharing_enabled
        }));
    } catch (error) {
        console.error('Error fetching campaigns:', error);
        throw error;
    }
}

/**
 * Get all pixels for a specific ad account
 */
export async function getPixels(adAccountId, authFetch) {
    try {
        const response = await authFetch(`${API_BASE_URL}/pixels?ad_account_id=${adAccountId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch pixels');
        }
        const pixels = await response.json();

        return pixels.map(pixel => ({
            id: pixel.id,
            name: pixel.name,
            code: pixel.code,
            isUnavailable: pixel.is_unavailable
        }));
    } catch (error) {
        console.error('Error fetching pixels:', error);
        throw error;
    }
}


/**
 * Get all promotable pages for a specific ad account
 */
export async function getPages(adAccountId, authFetch) {
    try {
        const query = adAccountId ? `?ad_account_id=${adAccountId}` : '';
        const response = await authFetch(`${API_BASE_URL}/pages${query}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch pages');
        }
        const pages = await response.json();

        return pages.map(page => ({
            id: page.id,
            name: page.name,
            category: page.category
        }));
    } catch (error) {
        console.error('Error fetching pages:', error);
        throw error;
    }
}


export const getAdSets = async (campaignId, adAccountId, authFetch) => {
    try {
        let url = `${API_BASE_URL}/adsets?`;
        if (campaignId) {
            url += `campaign_id=${campaignId}`;
        } else if (adAccountId) {
            url += `ad_account_id=${adAccountId}`;
        }

        const response = await authFetch(url);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to fetch ad sets');
        }
        const adSets = await response.json();
        return adSets;
    } catch (error) {
        console.error('Error fetching ad sets:', error);
        throw error;
    }
};

export const searchGeoLocations = async (query, adAccountId, authFetch) => {
    try {
        // Default to 'city' type for now, or we could make it a parameter
        // The backend supports 'city', 'region', 'country', 'zip', etc.
        // For general search, 'city' is common, but users might want countries.
        // Let's search for multiple types or default to a broad search if possible.
        // Facebook API 'location_types' can take multiple.

        // Let's use the searchLocations function we just added
        return await searchLocations(query, 'city', adAccountId, authFetch);
    } catch (error) {
        console.error('Error searching geo locations:', error);
        return [];
    }
};


/**
 * Upload video to Facebook
 * @param {string} videoUrl - URL of the video to upload
 * @param {string} adAccountId - Facebook ad account ID
 * @param {boolean} waitForReady - Whether to wait for video processing (default true)
 * @param {number} timeout - Max seconds to wait for processing (default 600)
 * @returns {Promise<{video_id: string, status: string, thumbnails: string[]}>}
 */
export async function uploadVideoToFacebook(videoUrl, adAccountId, authFetch, waitForReady = true, timeout = 600) {
    try {
        let finalVideoUrl = videoUrl;

        // If it's a blob URL, upload to our server first
        if (videoUrl.startsWith('blob:')) {
            const blobResponse = await fetch(videoUrl);
            const blob = await blobResponse.blob();

            const formData = new FormData();
            const extension = blob.type.split('/')[1] || 'mp4';
            formData.append('file', blob, `upload.${extension}`);

            const uploadResponse = await authFetch((import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1') + '/uploads/', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('Failed to upload video to server');
            }

            const uploadResult = await uploadResponse.json();
            finalVideoUrl = uploadResult.url;
        }

        const response = await authFetch(`${API_BASE_URL}/upload-video?ad_account_id=${adAccountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                video_url: finalVideoUrl,
                wait_for_ready: waitForReady,
                timeout: timeout
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload video to Facebook');
        }

        return await response.json();
    } catch (error) {
        console.error('Error uploading video:', error);
        throw error;
    }
}

/**
 * Get video processing status
 * @param {string} videoId - Facebook video ID
 * @returns {Promise<{status: string, video_id: string, length?: number}>}
 */
export async function getVideoStatus(videoId, authFetch) {
    try {
        const response = await authFetch(`${API_BASE_URL}/video-status/${videoId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get video status');
        }
        return await response.json();
    } catch (error) {
        console.error('Error getting video status:', error);
        throw error;
    }
}

/**
 * Get video thumbnails
 * @param {string} videoId - Facebook video ID
 * @returns {Promise<{thumbnails: string[]}>}
 */
export async function getVideoThumbnails(videoId, authFetch) {
    try {
        const response = await authFetch(`${API_BASE_URL}/video-thumbnails/${videoId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to get video thumbnails');
        }
        return await response.json();
    } catch (error) {
        console.error('Error getting video thumbnails:', error);
        throw error;
    }
}

/**
 * Upload a local File/Blob (or blob: URL) to our server, returning its public URL.
 * @param {File|Blob|string} fileOrBlobUrl
 * @param {string} [filename]
 * @returns {Promise<string>} public URL of the uploaded file
 */
export async function uploadBlobToServer(fileOrBlobUrl, authFetch, filename = 'upload.jpg') {
    let blob = fileOrBlobUrl;
    if (typeof fileOrBlobUrl === 'string') {
        const blobResponse = await fetch(fileOrBlobUrl);
        blob = await blobResponse.blob();
    }

    const formData = new FormData();
    formData.append('file', blob, blob.name || filename);

    const uploadResponse = await authFetch((import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1') + '/uploads/', {
        method: 'POST',
        body: formData
    });

    if (!uploadResponse.ok) {
        throw new Error('Failed to upload file to server');
    }

    const uploadResult = await uploadResponse.json();
    return uploadResult.url;
}

/**
 * Upload image to Facebook
 */
export async function uploadImageToFacebook(imageUrl, adAccountId, authFetch) {
    try {
        let finalImageUrl = imageUrl;

        // If it's a blob URL, we need to upload it to our server first
        if (imageUrl.startsWith('blob:')) {
            finalImageUrl = await uploadBlobToServer(imageUrl, authFetch);
        }

        const response = await authFetch(`${API_BASE_URL}/upload-image?ad_account_id=${adAccountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ image_url: finalImageUrl })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload image to Facebook');
        }

        const data = await response.json();
        return data.image_hash;
    } catch (error) {
        console.error('Error uploading image:', error);
        throw error;
    }
}

/**
 * Create Facebook Campaign
 */
export async function createFacebookCampaign(campaignData, adAccountId, authFetch) {
    try {
        const response = await authFetch(`${API_BASE_URL}/campaigns?ad_account_id=${adAccountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(campaignData)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create campaign');
        }

        const data = await response.json();
        return data.id;
    } catch (error) {
        console.error('Error creating campaign:', error);
        throw error;
    }
}

/**
 * Create Facebook Ad Set
 */
export async function createFacebookAdSet(adsetData, campaignId, adAccountId, budgetType, authFetch) {
    try {
        // Prepare payload for backend
        const payload = {
            ...adsetData,
            campaign_id: campaignId,
            budget_type: budgetType, // CBO or ABO - tells backend whether to set budget at adset level
            daily_budget: adsetData.dailyBudget, // Map camelCase to snake_case if needed, or handle in backend
            optimization_goal: adsetData.optimizationGoal,
            bid_strategy: adsetData.bidStrategy,
            bid_amount: adsetData.bidAmount,
            start_time: adsetData.startTime ? new Date(adsetData.startTime).toISOString() : null,
            targeting: adsetData.targeting
        };

        const response = await authFetch(`${API_BASE_URL}/adsets?ad_account_id=${adAccountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create ad set');
        }

        const data = await response.json();
        return data.id;
    } catch (error) {
        console.error('Error creating ad set:', error);
        throw error;
    }
}

/**
 * Create Facebook Ad Creative (supports both image and video)
 * @param {Object} creativeData - Creative data including bodies, headlines, websiteUrl
 * @param {string|null} imageHash - Image hash for image ads (null for video)
 * @param {string} pageId - Facebook page ID
 * @param {string} adAccountId - Facebook ad account ID
 * @param {Object|null} videoData - Video data: { video_id, thumbnail_url } for video ads
 */
export async function createFacebookCreative(creativeData, imageHash, pageId, adAccountId, authFetch, videoData = null) {
    try {
        const payload = {
            ...creativeData,
            page_id: pageId,
            primary_text: creativeData.bodies[0],
            headline: creativeData.headlines[0],
            website_url: creativeData.websiteUrl
        };

        // Add image or video data
        if (videoData && videoData.video_id) {
            payload.video_id = videoData.video_id;
            if (videoData.thumbnail_url) {
                payload.thumbnail_url = videoData.thumbnail_url;
            }
        } else if (imageHash) {
            payload.image_hash = imageHash;
        }

        const response = await authFetch(`${API_BASE_URL}/creatives?ad_account_id=${adAccountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create creative');
        }

        const data = await response.json();
        return data.id;
    } catch (error) {
        console.error('Error creating creative:', error);
        throw error;
    }
}

/**
 * Create Facebook Ad
 */
export async function createFacebookAd(adData, adsetId, creativeId, adAccountId, authFetch) {
    try {
        const payload = {
            ...adData,
            adset_id: adsetId,
            creative_id: creativeId
        };

        const response = await authFetch(`${API_BASE_URL}/ads?ad_account_id=${adAccountId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create ad');
        }

        const data = await response.json();
        return data.id;
    } catch (error) {
        console.error('Error creating ad:', error);
        throw error;
    }
}

/**
 * Search for locations
 */
export async function searchLocations(query, type = 'city', adAccountId, authFetch) {
    try {
        const response = await authFetch(`${API_BASE_URL}/locations/search?q=${encodeURIComponent(query)}&type=${type}&ad_account_id=${adAccountId}`);
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to search locations');
        }
        return await response.json();
    } catch (error) {
        console.error('Error searching locations:', error);
        throw error;
    }
}


/**
 * Campaign templates: reusable campaign+adset configs
 */
export async function getCampaignTemplates(authFetch) {
    const response = await authFetch(`${API_BASE_URL}/campaign-templates`);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch templates');
    }
    return await response.json();
}

export async function saveCampaignTemplate(name, config, authFetch) {
    const response = await authFetch(`${API_BASE_URL}/campaign-templates`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, config })
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to save template');
    }
    return await response.json();
}

export async function deleteCampaignTemplate(templateId, authFetch) {
    const response = await authFetch(`${API_BASE_URL}/campaign-templates/${templateId}`, { method: 'DELETE' });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete template');
    }
    return await response.json();
}

/**
 * Build the launch job payload from wizard state. Pure — unit tested.
 * @returns {Object} payload for POST /facebook/launches
 */
export function buildLaunchPayload({ campaignData, adsetData, creativeData, accounts, sourceAccountId, launchStatus, creatives }) {
    return {
        ad_account_ids: accounts,
        launch_status: launchStatus || 'PAUSED',
        source_account_id: sourceAccountId,
        campaign: {
            ...campaignData,
            dailyBudget: campaignData.dailyBudget ? Number(campaignData.dailyBudget) : null,
        },
        adset: {
            ...adsetData,
            dailyBudget: adsetData.dailyBudget ? Number(adsetData.dailyBudget) : null,
            bidAmount: adsetData.bidAmount ? Number(adsetData.bidAmount) : null,
            startTime: adsetData.startTime ? new Date(adsetData.startTime).toISOString() : null,
        },
        page_id: creativeData.pageId,
        instagram_id: creativeData.instagramId || null,
        creative_name: creativeData.creativeName,
        creatives,
        headlines: creativeData.headlines.filter(h => h && h.trim() !== ''),
        bodies: creativeData.bodies.filter(b => b && b.trim() !== ''),
        description: creativeData.description || null,
        cta: creativeData.cta || 'LEARN_MORE',
        website_url: creativeData.websiteUrl,
    };
}

/**
 * Queue a background multi-account launch job.
 * @param {Object} payload - Launch spec (ad_account_ids, campaign, adset, creatives, ...)
 * @returns {Promise<string>} job id
 */
export async function createLaunch(payload, authFetch) {
    const preflight = await preflightLaunch(payload, authFetch);
    const idempotencyKey = localStorage.getItem('launchIdempotencyKey') || crypto.randomUUID();
    localStorage.setItem('launchIdempotencyKey', idempotencyKey);
    const response = await authFetch(`${API_BASE_URL}/launches`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Idempotency-Key': idempotencyKey,
            'X-Preflight-Token': preflight.confirmation_token,
        },
        body: JSON.stringify(payload)
    });
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to queue launch');
    }
    const data = await response.json();
    localStorage.removeItem('launchIdempotencyKey');
    return data.job_id;
}

export async function preflightLaunch(payload, authFetch) {
    const response = await authFetch(`${API_BASE_URL}/launches/preflight`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Launch preflight failed');
    return data;
}

/**
 * Get the status of a launch job.
 * @param {string} jobId
 * @returns {Promise<Object>} job status with progress counters and per-entity results
 */
export async function getLaunch(jobId, authFetch) {
    const response = await authFetch(`${API_BASE_URL}/launches/${jobId}`);
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to fetch launch status');
    }
    return await response.json();
}

export async function preflightActivation(jobId, authFetch) {
    const response = await authFetch(`${API_BASE_URL}/launches/${jobId}/activation-preflight`, {
        method: 'POST',
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Activation preflight failed');
    return data;
}

export async function activateLaunch(jobId, confirmationToken, authFetch) {
    const response = await authFetch(`${API_BASE_URL}/launches/${jobId}/activate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation_token: confirmationToken }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Activation failed');
    return data;
}
