# AUTHORED, NOT RUN in Looker. Coverage needs a quarter filter on the explore, otherwise
# quota is summed across quarters and the ratio is meaningless.
view: quota {
  sql_table_name: quota ;;
  dimension: quarter { primary_key: yes  type: string  sql: ${TABLE}.quarter ;; }
  measure: quota_target { type: sum  sql: ${TABLE}.quota ;; value_format_name: usd_0 }

  # Open pipeline / (quota - closed won), evaluated per selected quarter.
  measure: coverage_ratio {
    type: number
    sql: ${opportunities.open_pipeline}
         / NULLIF(${quota_target} - ${opportunities.closed_won_amount}, 0) ;;
    value_format_name: decimal_2
  }
}
