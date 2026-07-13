import { describe, it, expect } from 'vitest';
import { buildLaunchPayload } from '../lib/facebookApi';

const baseArgs = {
    campaignData: { name: 'Camp', objective: 'OUTCOME_SALES', budgetType: 'ABO', dailyBudget: '25' },
    adsetData: { name: 'AdSet', optimizationGoal: 'OFFSITE_CONVERSIONS', dailyBudget: '10', bidAmount: '', startTime: '2026-08-01T01:00' },
    creativeData: {
        pageId: 'page_1',
        instagramId: null,
        creativeName: 'Creative',
        headlines: ['H1', '', 'H2'],
        bodies: ['B1', '  '],
        description: '',
        cta: 'SHOP_NOW',
        websiteUrl: 'https://example.com',
    },
    accounts: ['act_1', 'act_2'],
    sourceAccountId: 'act_1',
    launchStatus: 'PAUSED',
    creatives: [{ image_url: 'https://x/a.jpg', video_url: null, media_type: 'image', name: 'A' }],
};

describe('buildLaunchPayload', () => {
    it('builds a complete launch payload', () => {
        const payload = buildLaunchPayload(baseArgs);
        expect(payload.ad_account_ids).toEqual(['act_1', 'act_2']);
        expect(payload.launch_status).toBe('PAUSED');
        expect(payload.source_account_id).toBe('act_1');
        expect(payload.page_id).toBe('page_1');
        expect(payload.creatives).toHaveLength(1);
        expect(payload.cta).toBe('SHOP_NOW');
    });

    it('filters empty headlines and bodies', () => {
        const payload = buildLaunchPayload(baseArgs);
        expect(payload.headlines).toEqual(['H1', 'H2']);
        expect(payload.bodies).toEqual(['B1']);
    });

    it('converts numeric budgets and ISO start time', () => {
        const payload = buildLaunchPayload(baseArgs);
        expect(payload.campaign.dailyBudget).toBe(25);
        expect(payload.adset.dailyBudget).toBe(10);
        expect(payload.adset.bidAmount).toBeNull();
        expect(payload.adset.startTime).toMatch(/^\d{4}-\d{2}-\d{2}T.*Z$/);
    });

    it('defaults empty description to null and missing cta to LEARN_MORE', () => {
        const payload = buildLaunchPayload({
            ...baseArgs,
            creativeData: { ...baseArgs.creativeData, description: '', cta: '' },
        });
        expect(payload.description).toBeNull();
        expect(payload.cta).toBe('LEARN_MORE');
    });
});
