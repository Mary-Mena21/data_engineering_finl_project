
  
    
    

    create  table
      "warehouse"."main"."gold_author_stats__dbt_tmp"
  
    as (
      with silver as (
    select * from "warehouse"."main"."silver_books"
)
select
    author_name,
    count(*) as work_count,
    avg(edition_count)::int as avg_editions,
    min(first_publish_year) as first_published
from silver
where author_name is not null
group by author_name
order by work_count desc
    );
  
  