# Scheduled CSV export of the usage report

**Complexity:** 3

## Problem

Account admins of reportsvc need the monthly usage report outside the app. Today they screenshot the report page. Admins would love a better way to get this data.

## Users

Admins.

## Goals

- Admins can schedule a recurring CSV export of the usage report.
- Exports are delivered by email as a download link.
- Admins can see the history of past exports.

## Requirements

- R1: An admin can create a schedule (daily, weekly, monthly) for a usage-report export.
- R2: Each run generates a CSV of the usage report for the schedule's period.
- R3: The admin receives an email with a link to download the CSV.
- R4: The admin can view past exports and re-download them.
- R5: The admin can pause or delete a schedule.

## Non-goals

(none listed)

## Assumptions

- The usage report query is fast enough to run on a schedule.
