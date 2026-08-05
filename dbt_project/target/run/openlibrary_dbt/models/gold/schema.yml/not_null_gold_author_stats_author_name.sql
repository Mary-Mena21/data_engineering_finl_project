
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select author_name
from "warehouse"."main"."gold_author_stats"
where author_name is null



  
  
      
    ) dbt_internal_test