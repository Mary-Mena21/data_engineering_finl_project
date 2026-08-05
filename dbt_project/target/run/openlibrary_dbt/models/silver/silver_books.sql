
  
  create view "warehouse"."main"."silver_books__dbt_tmp" as (
    with raw as (
    -- unnest turns the list of works into one row per book
    select unnest(works) as work 
    from "warehouse"."main"."bronze_openlibrary_books"
)
select
    work.key as work_key,
    work.title,
    work.first_publish_year,
    -- authors is a list of structs inside each work
    work.authors[1]['name'] as author_name,
    work.edition_count
from raw
  );
