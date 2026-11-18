# AUTHORED, NOT RUN in Looker (see pipeline.model.lkml). SYNTHETIC data model only.

view: opportunities {
  sql_table_name: opportunities ;;

  dimension: opp_id { primary_key: yes  type: string  sql: ${TABLE}.opp_id ;; }
  dimension: owner { type: string  sql: ${TABLE}.owner ;; }
  dimension: segment { type: string  sql: ${TABLE}.segment ;; }
  dimension: stage { type: string  sql: ${TABLE}.stage ;; }
  dimension: forecast_category {
    type: string
    sql: ${TABLE}.forecast_category ;;
    suggestions: ["Commit", "Best Case", "Pipeline", "Closed"]
  }
  dimension: amount { type: number  sql: ${TABLE}.amount ;; value_format_name: usd_0 hidden: yes }
  dimension: is_won { type: yesno  sql: ${TABLE}.is_won = 1 ;; }
  dimension: is_closed { type: yesno  sql: ${TABLE}.is_closed = 1 ;; }
  dimension: is_open { type: yesno  sql: ${TABLE}.is_closed = 0 ;; }

  dimension_group: created {
    type: time  timeframes: [date, month, quarter, year]
    datatype: date  sql: ${TABLE}.created_date ;;
  }
  dimension_group: planned_close {
    type: time  timeframes: [date, month, quarter, year]
    datatype: date  sql: ${TABLE}.planned_close_date ;;
  }
  dimension_group: closed {
    type: time  timeframes: [date, month, quarter, year]
    datatype: date  sql: ${TABLE}.closed_date ;;
  }

  measure: count { type: count }
  measure: total_amount { type: sum  sql: ${amount} ;; value_format_name: usd_0 }

  measure: open_pipeline {
    type: sum  sql: ${amount} ;;
    filters: [is_open: "yes"]
    value_format_name: usd_0
  }

  # amount x stage probability, open deals only. Mirrors weighted_by_stage in sql/metrics.sql.
  measure: weighted_pipeline {
    type: sum
    sql: ${amount} * ${stage_prob.prob} ;;
    filters: [is_open: "yes"]
    value_format_name: usd_0
  }

  measure: commit_amount {
    type: sum  sql: ${amount} ;;
    filters: [is_open: "yes", forecast_category: "Commit"]
    value_format_name: usd_0
  }
  measure: best_case_amount {
    type: sum  sql: ${amount} ;;
    filters: [is_open: "yes", forecast_category: "Commit,Best Case"]
    value_format_name: usd_0
  }

  measure: won_count { type: count  filters: [is_won: "yes"] }
  measure: closed_count { type: count  filters: [is_closed: "yes"] }
  measure: win_rate {
    type: number
    sql: 1.0 * ${won_count} / NULLIF(${closed_count}, 0) ;;
    value_format_name: percent_1
  }
  measure: closed_won_amount {
    type: sum  sql: ${amount} ;;
    filters: [is_won: "yes"]
    value_format_name: usd_0
  }
  measure: avg_won_deal_size {
    type: average  sql: ${amount} ;;
    filters: [is_won: "yes"]
    value_format_name: usd_0
  }

  # Quarter label such as 2025Q4, used to join quota. Expression is SQLite-flavoured.
  dimension: planned_close_quarter_key {
    hidden: yes
    type: string
    sql: strftime('%Y', ${TABLE}.planned_close_date) || 'Q'
         || ((CAST(strftime('%m', ${TABLE}.planned_close_date) AS INTEGER) + 2) / 3) ;;
  }
}
