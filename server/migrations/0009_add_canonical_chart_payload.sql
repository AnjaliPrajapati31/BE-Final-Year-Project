ALTER TABLE analysis_result_payloads DROP CONSTRAINT IF EXISTS analysis_result_payloads_result_type_check;
ALTER TABLE analysis_result_payloads ADD CONSTRAINT analysis_result_payloads_result_type_check CHECK (
    result_type IN (
        'crop','growth_stage','moisture_stress','weather','water_balance',
        'irrigation_advisory','charts'
    )
);
