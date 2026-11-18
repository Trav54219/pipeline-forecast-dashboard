# AUTHORED, NOT RUN: this LookML was written by hand and has never been loaded into
# Looker, validated by the LookML validator, or queried. Treat it as a design sketch.
# It targets the tables in sql/schema.sql (SYNTHETIC demo data only).

connection: "pipeline_demo"

include: "/lookml/*.view.lkml"

explore: opportunities {
  label: "Pipeline & Forecast"
  description: "Opportunity-level pipeline with stage-probability weighting and quota coverage."

  join: stage_prob {
    type: left_outer
    relationship: many_to_one
    sql_on: ${opportunities.stage} = ${stage_prob.stage} ;;
  }

  join: quota {
    type: left_outer
    relationship: many_to_one
    sql_on: ${opportunities.planned_close_quarter_key} = ${quota.quarter} ;;
  }
}
