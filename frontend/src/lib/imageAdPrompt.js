function formatValue(value) {
  if (!value) return '';
  if (Array.isArray(value)) return value.join(', ');
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}

function addLine(lines, label, value) {
  const formatted = formatValue(value);
  if (formatted) {
    lines.push(`**${label}:** ${formatted}`);
  }
}

export function getTemplateIdForGeneratedAd(template) {
  return template?.type === 'template' ? template.id : null;
}

export function buildImageGenerationPrompt({ wizardData, copy }) {
  const template = wizardData?.template || {};
  const product = wizardData?.product || {};
  const brand = wizardData?.brand || {};
  const campaignDetails = wizardData?.campaignDetails || {};

  const sections = [];

  const blueprintLines = [];
  addLine(blueprintLines, 'Selected Template', template.name || template.template_category);
  addLine(blueprintLines, 'Template Category', template.category || template.template_category);
  addLine(blueprintLines, 'Template Blueprint', template.prompt);
  addLine(blueprintLines, 'Psychology', template.psychology);
  if (blueprintLines.length) {
    sections.push(blueprintLines.join('\n'));
  }

  const subjectLines = [];
  if (campaignDetails.angle) {
    addLine(subjectLines, 'Subject Matter', campaignDetails.angle);
  } else {
    addLine(subjectLines, 'Subject Matter', template.subject_matter || template.subject);
    if (template.topHalf || template.bottomHalf) {
      addLine(subjectLines, 'Split Layout', `Top: ${template.topHalf || 'N/A'}; Bottom: ${template.bottomHalf || 'N/A'}`);
    }
    if (template.leftSide || template.rightSide) {
      addLine(subjectLines, 'Comparison Layout', `Left: ${template.leftSide || 'N/A'}; Right: ${template.rightSide || 'N/A'}`);
    }
    addLine(subjectLines, 'Visual Layout', template.visualLayout);
  }
  addLine(subjectLines, 'Visual Anchors', template.visualAnchors);
  addLine(subjectLines, 'Visual Elements', template.visual_elements);
  addLine(subjectLines, 'Overlays', template.overlays);
  addLine(subjectLines, 'Composition', template.composition);
  if (template.id === 'iphone-note') {
    subjectLines.push('**Constraint:** Keep all visible text under 15 words total for legibility.');
  }
  if (subjectLines.length) {
    sections.push(subjectLines.join('\n'));
  }

  const brandLines = [];
  addLine(brandLines, 'Product', `${product.name || 'Product'}${product.description ? ` - ${product.description}` : ''}`);
  addLine(brandLines, 'Brand', `${brand.name || ''}${brand.voice ? ` (${brand.voice})` : ''}`);
  addLine(brandLines, 'Primary Brand Color', brand.colors?.primary);
  sections.push(brandLines.join('\n'));

  if (copy?.headline) {
    sections.push(`**Ad Copy Context:** Visual representation of "${copy.headline}"\n**CTA Context:** ${copy.cta || 'Primary call to action'}`);
  }

  const artLines = [];
  addLine(artLines, 'Mood', template.mood || 'Engaging');
  addLine(artLines, 'Lighting', template.lighting || 'Professional lighting');
  addLine(artLines, 'Design Style', template.design_style || 'Modern advertising design');
  sections.push(`**Art Direction:**\n${artLines.join('\n')}`);

  sections.push(
    '**Generation Requirements:** Follow the selected template blueprint literally. ' +
    'Make the output look like a finished paid social ad image, not a generic product photo. ' +
    'Do not render tiny unreadable paragraphs. Leave clean negative space where ad copy would be overlaid.'
  );

  sections.push('**Quality:** High quality, photorealistic, advertising-ready, sharp, polished, 4k detail.');

  return sections.filter(Boolean).join('\n\n');
}

export function buildImageVariationPrompt(basePrompt, variationIndex, totalVariations, size) {
  if (totalVariations <= 1) return basePrompt;

  const directions = [
    'Use the strongest product-first composition with clear hero framing.',
    'Use a distinct camera angle, prop arrangement, and background treatment.',
    'Use a bolder pattern interrupt while preserving the selected template structure.',
    'Use a tighter crop with stronger contrast and a more direct visual metaphor.',
  ];
  const direction = directions[variationIndex % directions.length];
  const sizeName = size?.name || 'selected size';

  return `${basePrompt}\n\n**Variation ${variationIndex + 1} of ${totalVariations}:** ${direction} Render for ${sizeName}. Do not reuse the exact same layout, camera angle, or object placement as the other variations.`;
}
