# AUTHORED, NOT RUN in Looker. Assumed stage probabilities (not measured).
view: stage_prob {
  sql_table_name: stage_prob ;;
  dimension: stage { primary_key: yes  type: string  sql: ${TABLE}.stage ;; }
  dimension: stage_order { type: number  sql: ${TABLE}.stage_order ;; }
  dimension: prob { type: number  sql: ${TABLE}.prob ;; value_format_name: percent_0 }
}
