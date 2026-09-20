export const STORY_CHAPTERS = [
  { id: 'crop', number: '01', eyebrow: 'RECOGNISE THE CROP', heading: 'Start with what is growing.', copy: 'Radar and optical observations build a seasonal view of the field. CropSense first classifies Paddy or Non-Paddy, because rice-specific analysis should only continue when the crop result supports it.', qualification: 'Satellite classification is evidence about the field—not a substitute for a field record.', tags: ['Sentinel-1', 'Sentinel-2', 'Paddy / Non-Paddy'] },
  { id: 'field', number: '08', eyebrow: 'YOUR FIELD', heading: 'Now bring your own field into view.', copy: 'The complete landscape is the context. Your polygon is where CropSense begins: validating the field, retrieving observations, and preserving the evidence behind each result.', qualification: 'This landscape is illustrative. Real field selection opens the operational field tool.', tags: ['Field polygon', 'Coverage checks', 'Analysis history'] },
];

export const STORY_COUNT = STORY_CHAPTERS.length;

