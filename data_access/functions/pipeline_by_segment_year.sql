CREATE OR REPLACE FUNCTION public.pipeline_by_segment_year()
RETURNS TABLE (
    year text,
    oppty_segment text,
    sql_pipeline double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        op_created_year AS year,
        oppty_segment,
        SUM(sql_pipe) AS sql_pipeline
    FROM public.hw_assignment_data
    WHERE sql_pipe IS NOT NULL
      AND op_created_year IN ('FY24', 'FY25', 'FY26')
      AND op_created_year IS NOT NULL
      AND oppty_segment IS NOT NULL
    GROUP BY op_created_year, oppty_segment
$$;
