import {
  buildImageGenerationPrompt,
  buildImageVariationPrompt,
  getTemplateIdForGeneratedAd,
} from './imageAdPrompt';

const baseWizardData = {
  brand: {
    name: 'Townsquare Interactive',
    voice: 'Helpful and direct',
    colors: { primary: '#f59e0b' },
  },
  product: {
    name: 'Local Marketing',
    description: 'Digital marketing for local businesses',
  },
  campaignDetails: {
    angle: '',
  },
};

const copy = {
  headline: 'Be Found Locally',
  body: 'Customers are searching. Show up first.',
  cta: 'Get Started',
};

test('image prompts include the selected style blueprint and differ by template', () => {
  const oldWayPrompt = buildImageGenerationPrompt({
    wizardData: {
      ...baseWizardData,
      template: {
        type: 'style',
        id: 'old-way-new-way',
        name: 'Old Way vs. New Way',
        visualLayout: 'Diagonal split',
        prompt: 'Diagonal split composition with black-and-white old way and vibrant new way.',
        psychology: 'Evolution and progress.',
        mood: 'Progressive',
        lighting: 'Contrasting',
        design_style: 'Modern vs vintage contrast',
      },
    },
    copy,
  });

  const notePrompt = buildImageGenerationPrompt({
    wizardData: {
      ...baseWizardData,
      template: {
        type: 'style',
        id: 'iphone-note',
        name: 'iPhone Note',
        visualLayout: 'Apple Notes screenshot',
        prompt: 'Exact replica of iPhone Notes app interface with short checklist copy.',
        psychology: 'Native camouflage.',
        mood: 'Casual',
        lighting: 'Screen glow',
        design_style: 'iOS native interface',
      },
    },
    copy,
  });

  expect(oldWayPrompt).toContain('Diagonal split composition');
  expect(notePrompt).toContain('iPhone Notes app');
  expect(oldWayPrompt).not.toEqual(notePrompt);
});

test('style archetypes are not saved as winning ad template ids', () => {
  expect(getTemplateIdForGeneratedAd({ type: 'style', id: 'old-way-new-way' })).toBeNull();
  expect(getTemplateIdForGeneratedAd({ type: 'template', id: 'winning-ad-123' })).toBe('winning-ad-123');
});

test('image variation prompts are distinct', () => {
  const first = buildImageVariationPrompt('Base prompt', 0, 3, { name: 'Square' });
  const second = buildImageVariationPrompt('Base prompt', 1, 3, { name: 'Square' });

  expect(first).toContain('Variation 1 of 3');
  expect(second).toContain('Variation 2 of 3');
  expect(first).not.toEqual(second);
});
