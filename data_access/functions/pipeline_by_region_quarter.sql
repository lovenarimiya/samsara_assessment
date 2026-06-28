CREATE OR REPLACE FUNCTION public.pipeline_by_region_quarter()
RETURNS TABLE (
    quarter_year text,
    year text,
    region text,
    sql_pipeline double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        op_created_quarter AS quarter_year,
        op_created_year AS year,
        oppty_region AS region,
        SUM(sql_pipe) AS sql_pipeline
    FROM public.hw_assignment_data
    WHERE sql_pipe IS NOT NULL
      AND op_created_year IN ('FY24', 'FY25', 'FY26')
      AND op_created_quarter IS NOT NULL
      AND op_created_year IS NOT NULL
      AND oppty_region IS NOT NULL
    GROUP BY op_created_quarter, op_created_year, oppty_region
$$;
