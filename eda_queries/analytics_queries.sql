--check header and data schema--
select * from hw_assignment_data limit 100

--get quarterly trend of pipeline and revenue(closed won pipeline) for FY24-FY26--
select
op_created_quarter,
sum(sql_pipe) as pipeline, 
sum(case when opportunity_stage = 'Closed Won' then sql_pipe else 0 end) As closed_won_pipe
from hw_assignment_data WHERE op_created_year IN ('FY24', 'FY25', 'FY26')
group by 1

--get yearly trend of pipeline and revenue(closed won pipeline) by Region--
select
op_created_year,
case when oppty_region = 'United States' then oppty_region else 'RoW' end as Opty_region,
sum(sql_pipe) as pipeline, 
sum(case when opportunity_stage = 'Closed Won' then sql_pipe else 0 end) As closed_won_pipe
from hw_assignment_data WHERE op_created_year IN ('FY24', 'FY25', 'FY26')
group by 1,2

--get yearly trend of pipeline and revenue(closed won pipeline) by account sector--
select
op_created_year,
account_sector,
sum(sql_pipe) as pipeline, 
sum(case when opportunity_stage = 'Closed Won' then sql_pipe else 0 end) As closed_won_pipe
from hw_assignment_data WHERE op_created_year IN ('FY24', 'FY25', 'FY26')
group by 1,2

--get yearly trend of pipeline and revenue(closed won pipeline) by account segment--
select
op_created_year,
oppty_segment,
sum(sql_pipe) as pipeline, 
sum(case when opportunity_stage = 'Closed Won' then sql_pipe else 0 end) As closed_won_pipe
from hw_assignment_data WHERE op_created_year IN ('FY24', 'FY25', 'FY26')
group by 1,2

--get top 5 campaign type by pipeline and revenue(closed won pipeline)--
SELECT
campaign_type,
sum(case when opportunity_stage = 'Closed Won' then sql_pipe else 0 end) As won_opp,
sum(sql_pipe) as pipeline,
CASE 
    WHEN SUM(sql_pipe) = 0 THEN 0 
    ELSE SUM(CASE WHEN opportunity_stage = 'Closed Won' THEN sql_pipe ELSE 0 END) / SUM(sql_pipe) 
    END AS win_rate
FROM hw_assignment_data
WHERE op_created_year IN ('FY24', 'FY25', 'FY26') 
group by 1
order by 3 desc limit 5

--get YoY trend for pipeline and revenue(closed won pipeline) by campaign type--

WITH campaign_totals AS (
    SELECT
        campaign_type,
        -- Total pipeline across both years to determine the top 5
        SUM(sql_pipe) AS total_pipeline,
        
        -- FY25 Metrics
        SUM(CASE WHEN opportunity_stage = 'Closed Won' AND op_created_year = 'FY25' THEN sql_pipe ELSE 0 END) AS FY25_won_opp,
        SUM(CASE WHEN op_created_year = 'FY25' THEN sql_pipe ELSE 0 END) AS FY25_pipeline,
        
        -- FY26 Metrics
        SUM(CASE WHEN opportunity_stage = 'Closed Won' AND op_created_year = 'FY26' THEN sql_pipe ELSE 0 END) AS FY26_won_opp,
        SUM(CASE WHEN op_created_year = 'FY26' THEN sql_pipe ELSE 0 END) AS FY26_pipeline
    FROM hw_assignment_data
    WHERE op_created_year IN ('FY25', 'FY26') 
    GROUP BY campaign_type
)
SELECT 
    campaign_type,
    FY25_won_opp,
    FY26_won_opp,
    FY25_pipeline,
    FY26_pipeline,
    
    -- Win Rates (with zero division guards)
    CASE WHEN FY25_pipeline = 0 THEN 0 ELSE FY25_won_opp * 1.0 / FY25_pipeline END AS FY25_win_rate,
    CASE WHEN FY26_pipeline = 0 THEN 0 ELSE FY26_won_opp * 1.0 / FY26_pipeline END AS FY26_win_rate,
    
    -- YoY Increase for Won Opp
    CASE WHEN FY25_won_opp = 0 THEN NULL ELSE (FY26_won_opp - FY25_won_opp) * 1.0 / FY25_won_opp END AS won_opp_yoy,
    
    -- YoY Increase for Pipeline
    CASE WHEN FY25_pipeline = 0 THEN NULL ELSE (FY26_pipeline - FY25_pipeline) * 1.0 / FY25_pipeline END AS pipeline_yoy,
    
    -- YoY Increase for Win Rate (Calculated as Win Rate Growth, not Basis Points)
    CASE 
        WHEN FY25_pipeline = 0 OR FY25_won_opp = 0 THEN NULL 
        ELSE (((FY26_won_opp * 1.0 / FY26_pipeline) - (FY25_won_opp * 1.0 / FY25_pipeline)) / (FY25_won_opp * 1.0 / FY25_pipeline)) 
    END AS win_rate_yoy
FROM campaign_totals
ORDER BY total_pipeline DESC 
LIMIT 5;

--What campaign type drove the most pipeline--
SELECT
op_created_year,
oppty_region,
account_sector,
campaign_type,
oppty_segment,
campaign_year,
count (distinct contact_id) as unique_lead,
sum(case when opportunity_stage = 'Closed Won' then sql_pipe else 0 end) As won_opp,
sum(sql_pipe) as pipeline
FROM hw_assignment_data
WHERE op_created_year IN ('FY24', 'FY25', 'FY26') 
group by 1,2,3,4,5,6
order by 9 desc

