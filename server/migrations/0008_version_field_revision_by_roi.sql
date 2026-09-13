ALTER TABLE field_revisions DROP CONSTRAINT IF EXISTS field_revisions_field_id_geometry_hash_key;
ALTER TABLE field_revisions ADD CONSTRAINT field_revisions_field_geometry_roi_key
    UNIQUE (field_id, geometry_hash, roi_id);
