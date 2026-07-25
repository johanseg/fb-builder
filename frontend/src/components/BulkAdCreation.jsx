import { useToast } from '../context/ToastContext';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Loader, Film, Image, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';
import { useCampaign } from '../context/CampaignContext';
import { useAuth } from '../context/AuthContext';
import {
    activateLaunch,
    buildLaunchPayload,
    createLaunch,
    getLaunch,
    preflightActivation,
    saveCampaignTemplate,
    uploadBlobToServer,
} from '../lib/facebookApi';

const POLL_INTERVAL_MS = 3000;
const RUNNING_STATUSES = ['queued', 'building', 'activation_queued', 'activating'];

const BulkAdCreation = ({ onNext, onBack }) => {
    const { showWarning, showError, showSuccess } = useToast();
    const { authFetch, hasPermission } = useAuth();
    const { campaignData, adsetData, creativeData, adsData, setAdsData, selectedAdAccount, extraAdAccounts } = useCampaign();
    // If a launch was running when the user navigated away, resume in the loading state
    const [resumeJobId] = useState(() => localStorage.getItem('lastLaunchJobId'));
    const [loading, setLoading] = useState(!!resumeJobId);
    const [job, setJob] = useState(null);
    const [statusText, setStatusText] = useState(resumeJobId ? 'Resuming launch in progress...' : '');
    const [activationPreview, setActivationPreview] = useState(null);
    const [activating, setActivating] = useState(false);
    const pollRef = useRef(null);

    // Preview of the permutation matrix the server will create
    React.useEffect(() => {
        if (creativeData.creatives && creativeData.creatives.length > 0) {
            const validHeadlines = creativeData.headlines.filter(h => h && h.trim() !== '');
            const validBodies = creativeData.bodies.filter(b => b && b.trim() !== '');

            const permutations = [];
            creativeData.creatives.forEach((creative, creativeIndex) => {
                validHeadlines.forEach((headline, hIndex) => {
                    validBodies.forEach((body, bIndex) => {
                        const isVideo = creative.mediaType === 'video';
                        const mediaLabel = isVideo ? 'Video' : 'Image';
                        permutations.push({
                            id: `ad_${creativeIndex}_${hIndex}_${bIndex}`,
                            name: `${creative.name || `${mediaLabel} ${creativeIndex + 1}`} - H${hIndex + 1}B${bIndex + 1}`,
                            creativeId: creative.id,
                            mediaType: creative.mediaType || 'image',
                        });
                    });
                });
            });

            setAdsData(permutations);
        } else {
            setAdsData([]);
        }
    }, [creativeData.creatives, creativeData.headlines, creativeData.bodies, setAdsData]);

    const stopPolling = useCallback(() => {
        if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
        }
    }, []);

    const startPolling = useCallback((jobId) => {
        stopPolling();
        const poll = async () => {
            try {
                const jobStatus = await getLaunch(jobId, authFetch);
                setJob(jobStatus);
                if (!RUNNING_STATUSES.includes(jobStatus.status)) {
                    stopPolling();
                    localStorage.removeItem('lastLaunchJobId');
                    setLoading(false);
                    if (jobStatus.status === 'ready') {
                        showSuccess(`Created ${jobStatus.completed_steps} paused ads across ${jobStatus.ad_account_ids.length} account(s)`);
                    } else if (jobStatus.status === 'active') {
                        showSuccess('Verified launch activated successfully');
                    } else if (jobStatus.status === 'reconciliation_required') {
                        showWarning('Launch requires reconciliation before it can be activated');
                    } else {
                        showError(`Launch failed: ${jobStatus.error || 'see results below'}`);
                    }
                }
            } catch (error) {
                console.error('Error polling launch job:', error);
            }
        };
        poll();
        pollRef.current = setInterval(poll, POLL_INTERVAL_MS);
    }, [authFetch, stopPolling, showSuccess, showWarning, showError]);

    // Resume polling if a launch was running when the user navigated away
    useEffect(() => {
        if (resumeJobId) {
            startPolling(resumeJobId);
        }
        return stopPolling;
    }, [resumeJobId, startPolling, stopPolling]);

    const handleSubmit = async () => {
        if (adsData.length === 0) {
            showWarning('Please add at least one ad');
            return;
        }
        if (!creativeData.pageId) {
            showWarning('Page ID is missing. Please go back to the Creative step and select a Facebook Page.');
            return;
        }

        setLoading(true);
        setJob(null);

        try {
            // 1. Any freshly-dropped files need a public URL before the server can push them to FB
            const creatives = [];
            for (const creative of creativeData.creatives || []) {
                const isVideo = creative.mediaType === 'video';
                let imageUrl = creative.imageUrl;
                let videoUrl = creative.videoUrl;
                if (creative.file) {
                    setStatusText(`Uploading ${creative.name}...`);
                    const url = await uploadBlobToServer(creative.file, authFetch, creative.name);
                    if (isVideo) videoUrl = url;
                    else imageUrl = url;
                } else if (!imageUrl && !videoUrl && creative.previewUrl && !creative.previewUrl.startsWith('blob:')) {
                    if (isVideo) videoUrl = creative.previewUrl;
                    else imageUrl = creative.previewUrl;
                }
                creatives.push({
                    image_url: imageUrl || null,
                    video_url: videoUrl || null,
                    thumbnail_url: creative.thumbnailUrl || null,
                    media_type: creative.mediaType || 'image',
                    name: creative.name || null,
                    module_ids: creative.moduleIds || [],
                });
            }

            // 2. Queue the server-side launch job
            setStatusText('Queueing launch...');
            const payload = buildLaunchPayload({
                campaignData,
                adsetData,
                creativeData,
                accounts: [selectedAdAccount.accountId, ...extraAdAccounts.map(a => a.accountId)],
                sourceAccountId: selectedAdAccount.accountId,
                launchStatus: 'PAUSED',
                creatives,
            });
            const jobId = await createLaunch(payload, authFetch);
            localStorage.setItem('lastLaunchJobId', jobId);

            // 3. Poll until done — the job keeps running even if this tab closes
            setStatusText('Launching...');
            startPolling(jobId);
        } catch (error) {
            console.error('Error queueing launch:', error);
            showError(`Error: ${error.message}`);
            setLoading(false);
        }
    };

    const handleActivationReview = async () => {
        try {
            setActivating(true);
            const preview = await preflightActivation(job.id, authFetch);
            setActivationPreview(preview);
        } catch (error) {
            showError(error.message);
        } finally {
            setActivating(false);
        }
    };

    const handleActivationConfirm = async () => {
        try {
            setActivating(true);
            await activateLaunch(job.id, activationPreview.confirmation_token, authFetch);
            setActivationPreview(null);
            setLoading(true);
            localStorage.setItem('lastLaunchJobId', job.id);
            startPolling(job.id);
        } catch (error) {
            showError(error.message);
        } finally {
            setActivating(false);
        }
    };

    const [savingTemplate, setSavingTemplate] = useState(false);
    const [templateName, setTemplateName] = useState('');
    const [showTemplateInput, setShowTemplateInput] = useState(false);

    const handleSaveTemplate = async () => {
        if (!templateName.trim()) {
            showWarning('Enter a template name');
            return;
        }
        setSavingTemplate(true);
        try {
            await saveCampaignTemplate(templateName.trim(), {
                campaign: { ...campaignData, id: null, fbCampaignId: null, isExisting: false },
                adset: { ...adsetData, id: null, fbAdsetId: null, isExisting: false },
                description: creativeData.description,
                cta: creativeData.cta,
                website_url: creativeData.websiteUrl,
            }, authFetch);
            showSuccess(`Template "${templateName.trim()}" saved`);
            setShowTemplateInput(false);
            setTemplateName('');
        } catch (error) {
            showError(`Failed to save template: ${error.message}`);
        } finally {
            setSavingTemplate(false);
        }
    };

    const totalAccounts = 1 + extraAdAccounts.length;
    const progressPct = job && job.total_steps > 0
        ? Math.round(((job.completed_steps + job.failed_steps) / job.total_steps) * 100)
        : 0;
    const adResults = (job?.results || []).filter(r => r.entity === 'ad' || r.error);

    return (
        <div>
            <h2 className="text-2xl font-bold mb-6">Review &amp; Launch</h2>
            <p className="text-muted-foreground mb-6">
                These ads will be created in the background — you can close this tab once the launch starts.
            </p>

            {/* Summary */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                <h3 className="font-semibold text-blue-900 mb-2">Summary</h3>
                <div className="text-sm text-blue-800 space-y-1">
                    <div><strong>Campaign:</strong> {campaignData.name}</div>
                    {campaignData.budgetType === 'CBO' && (
                        <div><strong>Campaign Budget:</strong> ${Number(campaignData.dailyBudget).toFixed(2)} / day</div>
                    )}
                    <div><strong>Ad Set:</strong> {adsetData.name}</div>
                    {campaignData.budgetType === 'ABO' && (
                        <div><strong>Ad Set Budget:</strong> ${Number(adsetData.dailyBudget).toFixed(2)} / day</div>
                    )}
                    <div><strong>Creative Name:</strong> {creativeData.creativeName}</div>
                    <div>
                        <strong>Media:</strong>{' '}
                        {(() => {
                            const images = creativeData.creatives?.filter(c => c.mediaType !== 'video').length || 0;
                            const videos = creativeData.creatives?.filter(c => c.mediaType === 'video').length || 0;
                            const parts = [];
                            if (images > 0) parts.push(`${images} image${images !== 1 ? 's' : ''}`);
                            if (videos > 0) parts.push(`${videos} video${videos !== 1 ? 's' : ''}`);
                            return parts.join(', ') || '0 files';
                        })()}
                    </div>
                    <div>
                        <strong>Accounts:</strong> {selectedAdAccount?.name}
                        {extraAdAccounts.length > 0 && ` + ${extraAdAccounts.length} more (${extraAdAccounts.map(a => a.name).join(', ')})`}
                    </div>
                    <div><strong>Total ads:</strong> {adsData.length * totalAccounts} ({adsData.length} per account × {totalAccounts} account{totalAccounts !== 1 ? 's' : ''})</div>
                </div>
            </div>

            {!loading ? (
                <>
                    {/* Ads preview list */}
                    <div className="space-y-2 mb-4">
                        {adsData.map((ad) => {
                            const creative = creativeData.creatives?.find(c => c.id === ad.creativeId);
                            const isVideo = creative?.mediaType === 'video';
                            return (
                                <div key={ad.id} className="flex items-center gap-3 p-3 bg-secondary rounded-lg border border-border">
                                    {creative && (
                                        <div className="w-12 h-12 rounded overflow-hidden bg-muted flex-shrink-0 relative">
                                            {isVideo ? (
                                                <>
                                                    <video src={creative.previewUrl} className="w-full h-full object-cover" muted />
                                                    <div className="absolute bottom-0 right-0 bg-purple-600 text-white p-0.5 rounded-tl">
                                                        <Film size={10} />
                                                    </div>
                                                </>
                                            ) : (
                                                <>
                                                    <img src={creative.previewUrl} alt="Thumbnail" className="w-full h-full object-cover" />
                                                    <div className="absolute bottom-0 right-0 bg-blue-600 text-white p-0.5 rounded-tl">
                                                        <Image size={10} />
                                                    </div>
                                                </>
                                            )}
                                        </div>
                                    )}
                                    <span className="text-sm text-foreground">{ad.name}</span>
                                </div>
                            );
                        })}
                    </div>

                    <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 mb-6">
                        <h3 className="font-semibold text-amber-900 text-sm">Safe launch state</h3>
                        <p className="text-xs text-amber-800 mt-1">
                            Every entity is created paused. A manager can review and activate the verified result after the build completes.
                        </p>
                    </div>

                    {/* Save as template */}
                    <div className="mb-2">
                        {showTemplateInput ? (
                            <div className="flex items-center gap-2">
                                <input
                                    type="text"
                                    value={templateName}
                                    onChange={(e) => setTemplateName(e.target.value)}
                                    placeholder="Template name..."
                                    className="px-3 py-2 border border-border rounded-lg text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                                />
                                <button
                                    onClick={handleSaveTemplate}
                                    disabled={savingTemplate}
                                    className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50"
                                >
                                    {savingTemplate ? 'Saving...' : 'Save'}
                                </button>
                                <button
                                    onClick={() => setShowTemplateInput(false)}
                                    className="px-3 py-2 text-muted-foreground text-sm hover:text-foreground"
                                >
                                    Cancel
                                </button>
                            </div>
                        ) : (
                            <button
                                onClick={() => setShowTemplateInput(true)}
                                className="text-sm text-amber-600 hover:text-amber-700 font-medium"
                            >
                                Save this setup as a template
                            </button>
                        )}
                    </div>

                    {/* Navigation */}
                    <div className="mt-8 flex justify-between">
                        <button
                            onClick={onBack}
                            className="px-6 py-3 text-muted-foreground hover:text-foreground font-medium"
                        >
                            Back
                        </button>
                        <button
                            onClick={handleSubmit}
                            disabled={adsData.length === 0}
                            className="flex items-center gap-2 px-6 py-3 text-white rounded-lg font-medium disabled:bg-gray-300 disabled:cursor-not-allowed bg-green-600 hover:bg-green-700"
                        >
                            Create {adsData.length * totalAccounts} Ad{adsData.length * totalAccounts !== 1 ? 's' : ''} Paused
                        </button>
                    </div>
                </>
            ) : (
                <div className="py-8">
                    {/* Progress */}
                    <div className="text-center mb-6">
                        <Loader className="animate-spin mx-auto mb-4 text-blue-600" size={40} />
                        <h3 className="text-xl font-semibold mb-2">
                            {job ? `Launching... ${job.completed_steps + job.failed_steps} of ${job.total_steps}` : statusText}
                        </h3>
                        <div className="w-full max-w-md mx-auto bg-muted rounded-full h-3 mb-2">
                            <div
                                className="bg-blue-600 h-3 rounded-full transition-all duration-300"
                                style={{ width: `${progressPct}%` }}
                            />
                        </div>
                        <p className="text-muted-foreground text-sm">
                            Runs in the background — you can safely leave this page.
                        </p>
                    </div>

                    {/* Per-account results */}
                    {adResults.length > 0 && (
                        <div className="max-w-2xl mx-auto space-y-1 max-h-64 overflow-y-auto">
                            {adResults.map((result, index) => (
                                <div key={index} className="flex items-center gap-2 text-sm px-3 py-1.5 bg-secondary rounded">
                                    {result.error
                                        ? <XCircle className="text-red-500 shrink-0" size={16} />
                                        : <CheckCircle2 className="text-green-600 shrink-0" size={16} />}
                                    <span className="text-muted-foreground shrink-0">{result.ad_account_id}</span>
                                    <span className="truncate">{result.name || result.entity}</span>
                                    {result.error && <span className="text-red-600 truncate ml-auto">{result.error}</span>}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Finished job results (shown after completion) */}
            {!loading && job && !RUNNING_STATUSES.includes(job.status) && (
                <div className="mt-6 max-w-2xl space-y-1">
                    <h3 className="font-semibold text-sm mb-2">
                        Last launch: {job.status.replace(/_/g, ' ')} — {job.completed_steps} created, {job.failed_steps} failed
                    </h3>
                    {adResults.filter(r => r.error).map((result, index) => (
                        <div key={index} className="flex items-center gap-2 text-sm px-3 py-1.5 bg-red-50 border border-red-200 rounded">
                            <XCircle className="text-red-500 shrink-0" size={16} />
                            <span className="text-muted-foreground shrink-0">{result.ad_account_id}</span>
                            <span className="truncate">{result.name || result.entity}</span>
                            <span className="text-red-600 truncate ml-auto">{result.error}</span>
                        </div>
                    ))}
                    {job.status === 'ready' && hasPermission('campaigns:activate') && (
                        <button
                            onClick={handleActivationReview}
                            disabled={activating}
                            className="mt-4 mr-3 px-6 py-3 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50"
                        >
                            {activating ? 'Verifying…' : 'Review Activation'}
                        </button>
                    )}
                    <button
                        onClick={onNext}
                        className="mt-4 px-6 py-3 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700"
                    >
                        Done
                    </button>
                </div>
            )}

            {activationPreview && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
                    <div className="w-full max-w-lg rounded-2xl bg-card border border-red-200 shadow-xl p-6">
                        <div className="flex items-center gap-3 text-red-700 mb-4">
                            <AlertTriangle size={24} />
                            <h3 className="text-xl font-bold">Activate verified Meta launch?</h3>
                        </div>
                        <p className="text-sm text-muted-foreground mb-4">
                            This changes the verified paused entities to ACTIVE and may begin spending real budget.
                        </p>
                        <div className="rounded-lg bg-secondary p-4 text-sm space-y-1 mb-6">
                            <div><strong>Campaign:</strong> {activationPreview.summary.campaign_name}</div>
                            <div><strong>Accounts:</strong> {activationPreview.summary.ad_account_ids.length}</div>
                            <div><strong>Ads:</strong> {activationPreview.summary.completed_steps}</div>
                            <div><strong>Current status:</strong> {activationPreview.summary.status}</div>
                        </div>
                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setActivationPreview(null)}
                                disabled={activating}
                                className="px-4 py-2 rounded-lg border border-border text-foreground"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleActivationConfirm}
                                disabled={activating}
                                className="px-4 py-2 rounded-lg bg-red-600 text-white font-semibold disabled:opacity-50"
                            >
                                {activating ? 'Activating…' : 'Activate in Meta'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default BulkAdCreation;
