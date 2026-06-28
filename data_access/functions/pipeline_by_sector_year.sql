CREATE OR REPLACE FUNCTION public.pipeline_by_sector_year()
RETURNS TABLE (
    year text,
    account_sector text,
    sql_pipeline double precision
)
LANGUAGE sql
STABLE
AS $$
    SELECT
        op_created_year AS year,
        account_sector,
        SUM(sql_pipe) AS sql_pipeline
    FROM public.hw_assignment_data
    WHERE sql_pipe IS NOT NULL
      AND op_created_year IN ('FY24', 'FY25', 'FY26')
      AND op_created_year IS NOT NULL
      AND account_sector IN ('Public', 'Private')
    GROUP BY op_created_year, account_sector
$$;
