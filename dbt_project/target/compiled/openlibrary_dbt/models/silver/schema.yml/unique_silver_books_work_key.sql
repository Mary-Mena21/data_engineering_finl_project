
    
    

select
    work_key as unique_field,
    count(*) as n_records

from "warehouse"."main"."silver_books"
where work_key is not null
group by work_key
having count(*) > 1


