# PRODUCT_LOGIC_SPEC — pr-fanout
Status: READY
Upstream decision: adversary-map 2026-09-13 (§5 rewritten sentence, §4 spec promotions), after kill-report-convergence killed three earlier candidate claims
Target runtime: other

## 1. Product truth

For someone who contributed honestly and got buried under agent-generated noise, this publishes — from public event data alone — how widely pull requests are sprayed across repositories, year by year, and what share comes from declared coding agents.

Observable success: a reader runs `pr-fanout collect --date 2025-09-10` and obtains the aggregate numbers published in the README, with the count of withheld small cells printed alongside.

Observable failure: the run emits a dataset built from trimmed archive hours, or emits a row that could identify an individual contributor.

Non-goals, each one an adversary's disarmament promoted to contract:

| Non-goal | Adversary it disarms |
|---|---|
| no logins of natural persons in any output | GitHub Site Policy — its research permission covers *public, non-personal* information only, and requires open access |
| no row below the minimum cell size | the identifiable contributor in a small repository (GDPR) |
| no repository ranked by rejection rate | the maintainer already coping by auto-closing everything, who would be shamed by a league table |
| no gating, scoring, or auto-close feature | the first-time contributor, who loses if "tell the honest ones apart" becomes an entry barrier |
| no reputation product built on this data | ourselves, three months from now, when monetisation turns aggregates into profiling |

## 2. Primary loop and invariants

`RUN_REQUESTED → fetch one archive hour → settle it under D-HOUR → decrement the sample → when the day is covered, aggregate → suppress small cells → write the dataset file`.

Four invariants carry the intent:

- **INV-1 / INV-2** keep the counters honest; a negative remaining-hours would mean an hour was counted twice.
- **INV-3** is the one that matters. The hour request is owned only while `fetching`, so a response that arrives after the run has moved on cannot be applied. This is the class of bug that produced today's wrong headline — a number that looked settled but was assembled from the wrong thing.
- **INV-4** makes suppression visible. Withholding rows is fine; withholding the fact that rows were withheld is not, so the count is published.

**Explicit limitation.** "No login of a natural person appears in any output" cannot be written in the gate's oracle DSL — it is a property of emitted strings, not of a numeric datum. It is enforced instead by a unit test that walks every key and value of a produced dataset and fails on any human account name. That test, not this contract, is its proof.

## 3. State, event, data, and effect explanation

`fetching` is the only state that owns a request, and `D-HOUR` is its only settle path. Its `stale` case exists so a late or orphaned response is discarded by rule rather than by luck. `empty` is a real outcome, not an error: the archive does not publish every hour, and a run that silently treated a missing hour as zero activity would understate every denominator.

`error` and `timeout` are terminal on purpose. The collector already retries inside `E-FETCH` with backoff; an outcome that surfaces means the retry budget is spent, and half a day of hours is worse than no day at all — a partial sample looks like a finding.

Suppression and the file write are modelled as data updates, not as effects. Writing the same date twice from the same archive bytes yields a byte-identical file, so the write is idempotent by construction and carries no reconciliation obligation; declaring it irreversible would add an idempotency key that nothing could ever disambiguate.

## 4. Motion and runtime rationale

No semantic motion exists. The artifact is a dataset, a README table, and two static SVG charts; nothing changes state in front of a viewer, so any animation would be decoration and is omitted rather than invented.

- **Remotion: not_applicable.** There is no trace a viewer replays. A rendered video would carry numbers away from the code that produced them, which is the opposite of what this artifact is for.
- **3D: not_applicable.** The output is one series over time. A third dimension would encode nothing.
- Two static SVGs (light and dark) rather than one theme-aware file, because GitHub's image proxy strips `<style>` and ignores `prefers-color-scheme` inside `<img>`.

## 5. Canonical contract

```json product-logic-contract
{
  "schema_version": "product-logic-contract/1",
  "status": "READY",
  "approval": {
    "decision": "approved",
    "by": "Felix",
    "at": "2026-09-13"
  },
  "product": {
    "name": "pr-fanout",
    "promise": "Anyone can reproduce, for any day of public GitHub history, how widely pull requests were sprayed across repositories and what share came from declared coding agents.",
    "success": "A reader runs `pr-fanout collect` on a date and obtains the same aggregate numbers published in the README, with every suppressed small cell accounted for.",
    "failure": "The run emits a dataset whose schema was trimmed, or whose rows could identify an individual contributor.",
    "non_goals": [
      "scoring or ranking individual contributors",
      "publishing logins of natural persons",
      "ranking repositories by rejection rate",
      "blocking, gating or auto-closing any pull request",
      "any reputation product built on this data"
    ]
  },
  "runtime": {
    "target": "other",
    "canonical_state_owner": "collector-reducer",
    "renderers": [
      "dom"
    ],
    "remotion_disposition": "not_applicable",
    "remotion_reason": "the artifact is a dataset and a README; there is no trace a viewer replays, and a rendered video would present numbers without the code that produced them",
    "three_d_disposition": "not_applicable",
    "three_d_reason": "the output is a one-series distribution over time; a third spatial dimension would encode nothing",
    "verification_surfaces": [
      "browser"
    ]
  },
  "lifecycle": {
    "back": {
      "disposition": "not_applicable",
      "rule": "a batch collector has no navigation stack",
      "event_ids": [],
      "state_ids": [],
      "transition_ids": [],
      "trace_ids": []
    },
    "offline": {
      "disposition": "not_applicable",
      "rule": "loss of connectivity surfaces as the bounded-retry error outcome of E-FETCH and produces no distinct product behavior",
      "event_ids": [],
      "state_ids": [],
      "transition_ids": [],
      "trace_ids": []
    },
    "duplicate_input": {
      "disposition": "handled",
      "rule": "a second RUN_REQUESTED while fetching is ignored so one run owns the output path",
      "event_ids": [
        "RUN_REQUESTED"
      ],
      "state_ids": [
        "fetching"
      ],
      "transition_ids": [],
      "trace_ids": [
        "TRACE-DUPLICATE"
      ]
    },
    "app_hidden": {
      "disposition": "handled",
      "rule": "interruption cancels the owned hour request and then persists progress",
      "event_ids": [
        "RUN_INTERRUPTED"
      ],
      "state_ids": [
        "fetching",
        "suspended"
      ],
      "transition_ids": [
        "T-INTERRUPT"
      ],
      "trace_ids": [
        "TRACE-SUSPEND"
      ]
    },
    "resume": {
      "disposition": "handled",
      "rule": "resume restores progress and takes ownership of a new hour request",
      "event_ids": [
        "RUN_RESUMED"
      ],
      "state_ids": [
        "suspended",
        "fetching"
      ],
      "transition_ids": [
        "T-RESUME"
      ],
      "trace_ids": [
        "TRACE-SUSPEND"
      ]
    },
    "expiry": {
      "disposition": "not_applicable",
      "rule": "no record expires; archive schema drift is detected per hour and recorded rather than aged out",
      "event_ids": [],
      "state_ids": [],
      "transition_ids": [],
      "trace_ids": []
    }
  },
  "primary_loop": {
    "id": "LOOP-1",
    "entry_state": "idle",
    "cycle_state": "fetching",
    "terminal_states": [
      "complete"
    ]
  },
  "invariants": [
    {
      "id": "INV-1",
      "rule": "hours still to fetch is never negative",
      "oracle": {
        "kind": "integer_min",
        "data": "hours_remaining",
        "min": 0
      }
    },
    {
      "id": "INV-2",
      "rule": "days written is never negative",
      "oracle": {
        "kind": "integer_min",
        "data": "days_collected",
        "min": 0
      }
    },
    {
      "id": "INV-3",
      "rule": "an hour request is owned only while fetching, so a settled response can never be applied after the run left that state",
      "oracle": {
        "kind": "nullable_only_in_states",
        "data": "active_request_id",
        "allowed_states": [
          "fetching"
        ]
      }
    },
    {
      "id": "INV-4",
      "rule": "the count of rows suppressed for small cell size is never negative; it is published so readers can see how much was withheld",
      "oracle": {
        "kind": "integer_min",
        "data": "suppressed_rows",
        "min": 0
      }
    }
  ],
  "data": [
    {
      "id": "hours_remaining",
      "type": "integer",
      "owner": "collector-reducer",
      "initial": 0,
      "persistence": "session",
      "invariant_ids": [
        "INV-1"
      ]
    },
    {
      "id": "days_collected",
      "type": "integer",
      "owner": "collector-reducer",
      "initial": 0,
      "persistence": "session",
      "invariant_ids": [
        "INV-2"
      ]
    },
    {
      "id": "active_request_id",
      "type": "nullable-string",
      "owner": "collector-reducer",
      "initial": null,
      "persistence": "none",
      "invariant_ids": [
        "INV-3"
      ]
    },
    {
      "id": "suppressed_rows",
      "type": "integer",
      "owner": "collector-reducer",
      "initial": 0,
      "persistence": "none",
      "invariant_ids": [
        "INV-4"
      ]
    }
  ],
  "states": [
    {
      "id": "idle",
      "kind": "initial",
      "unexpected_event": "reject",
      "unexpected_reason": "no run has started"
    },
    {
      "id": "fetching",
      "kind": "active",
      "unexpected_event": "ignore",
      "unexpected_reason": "a run already owns the output path"
    },
    {
      "id": "aggregating",
      "kind": "active",
      "unexpected_event": "ignore",
      "unexpected_reason": "counting is in progress and owns no request"
    },
    {
      "id": "emitting",
      "kind": "active",
      "unexpected_event": "ignore",
      "unexpected_reason": "the dataset file is being written"
    },
    {
      "id": "suspended",
      "kind": "suspended",
      "unexpected_event": "ignore",
      "unexpected_reason": "the run is parked and owns no request"
    },
    {
      "id": "complete",
      "kind": "terminal",
      "unexpected_event": "reject",
      "unexpected_reason": "the dataset for this date is written"
    },
    {
      "id": "failed",
      "kind": "error",
      "unexpected_event": "reject",
      "unexpected_reason": "the run ended without a dataset and waits for a fresh request"
    }
  ],
  "events": [
    {
      "id": "RUN_REQUESTED",
      "source": "user",
      "payload": {
        "request_id": {
          "type": "string",
          "nonempty": true
        }
      }
    },
    {
      "id": "HOUR_SETTLED",
      "source": "provider",
      "payload": {
        "request_id": {
          "type": "string",
          "nonempty": true
        },
        "result_kind": {
          "type": "enum",
          "values": [
            "success",
            "empty",
            "error",
            "timeout"
          ]
        }
      }
    },
    {
      "id": "ALL_HOURS_DONE",
      "source": "system",
      "payload": {}
    },
    {
      "id": "AGGREGATE_DONE",
      "source": "system",
      "payload": {
        "suppressed_rows": {
          "type": "integer",
          "min": 0
        }
      }
    },
    {
      "id": "EMIT_DONE",
      "source": "system",
      "payload": {}
    },
    {
      "id": "RUN_INTERRUPTED",
      "source": "lifecycle",
      "lifecycle_kind": "app_hidden",
      "payload": {}
    },
    {
      "id": "RUN_RESUMED",
      "source": "lifecycle",
      "lifecycle_kind": "resume",
      "payload": {
        "request_id": {
          "type": "string",
          "nonempty": true
        }
      }
    },
    {
      "id": "NEXT_HOUR",
      "source": "system",
      "payload": {
        "request_id": {
          "type": "string",
          "nonempty": true
        }
      }
    }
  ],
  "decision_tables": [
    {
      "id": "D-HOUR",
      "state": "fetching",
      "event": "HOUR_SETTLED",
      "cases": [
        "stale",
        "success",
        "empty",
        "error",
        "timeout"
      ],
      "case_rules": [
        {
          "case": "stale",
          "outcome": "stale",
          "description": "a response from a request this state no longer owns cannot change anything",
          "when": [
            {
              "left": {
                "event": "request_id"
              },
              "op": "ne",
              "right": {
                "data": "active_request_id"
              }
            }
          ]
        },
        {
          "case": "success",
          "outcome": "success",
          "description": "the owned hour arrived with a full payload schema",
          "when": [
            {
              "left": {
                "event": "request_id"
              },
              "op": "eq",
              "right": {
                "data": "active_request_id"
              }
            },
            {
              "left": {
                "event": "result_kind"
              },
              "op": "eq",
              "right": {
                "literal": "success"
              }
            }
          ]
        },
        {
          "case": "empty",
          "outcome": "empty",
          "description": "the owned hour is not published by the archive; the run continues with one hour fewer",
          "when": [
            {
              "left": {
                "event": "request_id"
              },
              "op": "eq",
              "right": {
                "data": "active_request_id"
              }
            },
            {
              "left": {
                "event": "result_kind"
              },
              "op": "eq",
              "right": {
                "literal": "empty"
              }
            }
          ]
        },
        {
          "case": "error",
          "outcome": "error",
          "description": "the owned hour failed after bounded retries",
          "when": [
            {
              "left": {
                "event": "request_id"
              },
              "op": "eq",
              "right": {
                "data": "active_request_id"
              }
            },
            {
              "left": {
                "event": "result_kind"
              },
              "op": "eq",
              "right": {
                "literal": "error"
              }
            }
          ]
        },
        {
          "case": "timeout",
          "outcome": "timeout",
          "description": "the owned hour exhausted its retry budget on timeouts",
          "when": [
            {
              "left": {
                "event": "request_id"
              },
              "op": "eq",
              "right": {
                "data": "active_request_id"
              }
            },
            {
              "left": {
                "event": "result_kind"
              },
              "op": "eq",
              "right": {
                "literal": "timeout"
              }
            }
          ]
        }
      ],
      "evaluation_order": [
        "stale",
        "success",
        "empty",
        "error",
        "timeout"
      ],
      "exclusive": true,
      "exhaustive": true,
      "default_case": "error"
    }
  ],
  "effects": [
    {
      "id": "E-FETCH",
      "kind": "async",
      "owner": "collector-reducer",
      "operation": "fetch_archive_hour",
      "outcomes": {
        "success": "success",
        "empty": "empty",
        "error": "error",
        "timeout": "timeout",
        "cancel": "not_applicable",
        "stale": "stale"
      },
      "decision_table": "D-HOUR",
      "settle_event": "HOUR_SETTLED",
      "request_id_data": "active_request_id",
      "stale_policy": "discard the response without touching state",
      "cancel_policy": "cancel every owned request before the run is parked"
    },
    {
      "id": "E-CANCEL",
      "kind": "sync",
      "owner": "collector-reducer",
      "operation": "cancel_request",
      "data_ids": [
        "active_request_id"
      ]
    },
    {
      "id": "E-PERSIST",
      "kind": "sync",
      "owner": "collector-reducer",
      "operation": "persist_session",
      "data_ids": [
        "hours_remaining",
        "days_collected"
      ]
    },
    {
      "id": "E-RESTORE",
      "kind": "sync",
      "owner": "collector-reducer",
      "operation": "restore_session",
      "data_ids": [
        "hours_remaining",
        "days_collected"
      ]
    }
  ],
  "transitions": [
    {
      "id": "T-RUN",
      "from": "idle",
      "event": "RUN_REQUESTED",
      "to": "fetching",
      "effects": [
        "E-FETCH"
      ],
      "updates": [
        {
          "data": "hours_remaining",
          "operation": "set",
          "args": {
            "value": 12
          },
          "rule": "a reference day samples every second hour"
        },
        {
          "data": "active_request_id",
          "operation": "set_from_event",
          "args": {
            "field": "request_id"
          },
          "rule": "the run takes ownership of the first hour request"
        }
      ],
      "motion_ids": [],
      "feedback": "the run prints the date it is collecting",
      "scenario_ids": [
        "TRACE-HAPPY",
        "TRACE-FAILURE",
        "TRACE-SUSPEND",
        "TRACE-EDGE",
        "TRACE-DUPLICATE"
      ]
    },
    {
      "id": "T-HOUR-STALE",
      "from": "fetching",
      "event": "HOUR_SETTLED",
      "to": "fetching",
      "decision_table": "D-HOUR",
      "case": "stale",
      "effects": [],
      "updates": [],
      "motion_ids": [],
      "feedback": "nothing is printed; the response is discarded",
      "scenario_ids": [
        "TRACE-EDGE"
      ]
    },
    {
      "id": "T-HOUR-SUCCESS",
      "from": "fetching",
      "event": "HOUR_SETTLED",
      "to": "fetching",
      "decision_table": "D-HOUR",
      "case": "success",
      "effects": [],
      "updates": [
        {
          "data": "hours_remaining",
          "operation": "increment",
          "args": {
            "amount": -1
          },
          "rule": "one sampled hour is accounted for"
        },
        {
          "data": "active_request_id",
          "operation": "clear",
          "args": {},
          "rule": "the settled hour releases ownership, so a late duplicate of it can never be applied"
        }
      ],
      "motion_ids": [],
      "feedback": "the hour tag and its opened-PR count are printed",
      "scenario_ids": [
        "TRACE-HAPPY",
        "TRACE-FAILURE",
        "TRACE-SUSPEND"
      ]
    },
    {
      "id": "T-HOUR-EMPTY",
      "from": "fetching",
      "event": "HOUR_SETTLED",
      "to": "fetching",
      "decision_table": "D-HOUR",
      "case": "empty",
      "effects": [],
      "updates": [
        {
          "data": "hours_remaining",
          "operation": "increment",
          "args": {
            "amount": -1
          },
          "rule": "an unpublished hour still shortens the sample and is recorded as not collected"
        },
        {
          "data": "active_request_id",
          "operation": "clear",
          "args": {},
          "rule": "the settled hour releases ownership, so a late duplicate of it can never be applied"
        }
      ],
      "motion_ids": [],
      "feedback": "the hour is printed as not published",
      "scenario_ids": [
        "TRACE-EDGE"
      ]
    },
    {
      "id": "T-HOUR-ERROR",
      "from": "fetching",
      "event": "HOUR_SETTLED",
      "to": "failed",
      "decision_table": "D-HOUR",
      "case": "error",
      "effects": [],
      "updates": [
        {
          "data": "active_request_id",
          "operation": "clear",
          "args": {},
          "rule": "a terminal state owns no request"
        }
      ],
      "motion_ids": [],
      "feedback": "the failing hour and its reason are printed, and no dataset file is written",
      "scenario_ids": [
        "TRACE-FAILURE"
      ]
    },
    {
      "id": "T-HOUR-TIMEOUT",
      "from": "fetching",
      "event": "HOUR_SETTLED",
      "to": "failed",
      "decision_table": "D-HOUR",
      "case": "timeout",
      "effects": [],
      "updates": [
        {
          "data": "active_request_id",
          "operation": "clear",
          "args": {},
          "rule": "a terminal state owns no request"
        }
      ],
      "motion_ids": [],
      "feedback": "the timed-out hour is printed, and no dataset file is written",
      "scenario_ids": [
        "TRACE-EDGE"
      ]
    },
    {
      "id": "T-ALL-DONE",
      "from": "fetching",
      "event": "ALL_HOURS_DONE",
      "to": "aggregating",
      "effects": [],
      "updates": [],
      "motion_ids": [],
      "feedback": "the run stops printing hours and begins counting",
      "scenario_ids": [
        "TRACE-HAPPY",
        "TRACE-FAILURE",
        "TRACE-SUSPEND"
      ]
    },
    {
      "id": "T-AGG",
      "from": "aggregating",
      "event": "AGGREGATE_DONE",
      "to": "emitting",
      "effects": [],
      "updates": [
        {
          "data": "suppressed_rows",
          "operation": "set_from_event",
          "args": {
            "field": "suppressed_rows"
          },
          "rule": "rows below the minimum cell size are withheld, and how many were withheld is itself published"
        }
      ],
      "motion_ids": [],
      "feedback": "the number of suppressed small cells is printed",
      "scenario_ids": [
        "TRACE-HAPPY",
        "TRACE-FAILURE",
        "TRACE-SUSPEND"
      ]
    },
    {
      "id": "T-EMIT",
      "from": "emitting",
      "event": "EMIT_DONE",
      "to": "complete",
      "effects": [],
      "updates": [
        {
          "data": "days_collected",
          "operation": "increment",
          "args": {
            "amount": 1
          },
          "rule": "one reference day is now on disk"
        }
      ],
      "motion_ids": [],
      "feedback": "the output path is printed",
      "scenario_ids": [
        "TRACE-HAPPY",
        "TRACE-FAILURE",
        "TRACE-SUSPEND"
      ]
    },
    {
      "id": "T-INTERRUPT",
      "from": "fetching",
      "event": "RUN_INTERRUPTED",
      "to": "suspended",
      "effects": [
        "E-CANCEL",
        "E-PERSIST"
      ],
      "updates": [
        {
          "data": "active_request_id",
          "operation": "clear",
          "args": {},
          "rule": "the owned request is released before progress is written, so a response that arrives later cannot be applied"
        }
      ],
      "motion_ids": [],
      "feedback": "the run reports how many hours it had already collected",
      "policy_kind": "app_hidden",
      "scenario_ids": [
        "TRACE-SUSPEND"
      ]
    },
    {
      "id": "T-RESUME",
      "from": "suspended",
      "event": "RUN_RESUMED",
      "to": "fetching",
      "effects": [
        "E-RESTORE"
      ],
      "updates": [
        {
          "data": "active_request_id",
          "operation": "set_from_event",
          "args": {
            "field": "request_id"
          },
          "rule": "resuming takes ownership of a fresh request rather than trusting the cancelled one"
        }
      ],
      "motion_ids": [],
      "feedback": "the run reports the hour it is resuming from",
      "policy_kind": "resume",
      "scenario_ids": [
        "TRACE-SUSPEND"
      ]
    },
    {
      "id": "T-RETRY",
      "from": "failed",
      "event": "RUN_REQUESTED",
      "to": "fetching",
      "effects": [
        "E-FETCH"
      ],
      "updates": [
        {
          "data": "hours_remaining",
          "operation": "set",
          "args": {
            "value": 12
          },
          "rule": "a retry re-samples the whole day rather than stitching a partial one"
        },
        {
          "data": "active_request_id",
          "operation": "set_from_event",
          "args": {
            "field": "request_id"
          },
          "rule": "the retry owns a new request"
        }
      ],
      "motion_ids": [],
      "feedback": "the run restarts and prints the date again",
      "scenario_ids": [
        "TRACE-FAILURE"
      ]
    },
    {
      "id": "T-NEXT",
      "from": "fetching",
      "event": "NEXT_HOUR",
      "to": "fetching",
      "effects": [
        "E-FETCH"
      ],
      "updates": [
        {
          "data": "active_request_id",
          "operation": "set_from_event",
          "args": {
            "field": "request_id"
          },
          "rule": "the run takes ownership of exactly one hour at a time"
        }
      ],
      "motion_ids": [],
      "feedback": "the next hour tag is printed as it starts",
      "scenario_ids": [
        "TRACE-HAPPY",
        "TRACE-EDGE"
      ]
    }
  ],
  "motions": [],
  "assets": [],
  "traces": [
    {
      "id": "TRACE-HAPPY",
      "kind": "happy",
      "initial_state": "idle",
      "fixtures": {
        "seed": 1,
        "initial_data": {},
        "provider_outcomes": [
          "success",
          "success"
        ]
      },
      "steps": [
        {
          "event": "RUN_REQUESTED",
          "input": {
            "request_id": "run-1-h0"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "hours_remaining": 12,
            "active_request_id": "run-1-h0"
          },
          "expect_feedback": "the run prints the date it is collecting"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-1-h0",
            "result_kind": "success"
          },
          "expect_state": "fetching",
          "expect_effects": [],
          "expect_data": {
            "hours_remaining": 11,
            "active_request_id": null
          },
          "expect_feedback": "the hour tag and its opened-PR count are printed",
          "case": "success"
        },
        {
          "event": "NEXT_HOUR",
          "input": {
            "request_id": "run-1-h1"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "active_request_id": "run-1-h1"
          },
          "expect_feedback": "the next hour tag is printed as it starts"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-1-h1",
            "result_kind": "success"
          },
          "expect_state": "fetching",
          "expect_effects": [],
          "expect_data": {
            "hours_remaining": 10,
            "active_request_id": null
          },
          "expect_feedback": "the hour tag and its opened-PR count are printed",
          "case": "success"
        },
        {
          "event": "ALL_HOURS_DONE",
          "input": {},
          "expect_state": "aggregating",
          "expect_effects": [],
          "expect_data": {},
          "expect_feedback": "the run stops printing hours and begins counting"
        },
        {
          "event": "AGGREGATE_DONE",
          "input": {
            "suppressed_rows": 4
          },
          "expect_state": "emitting",
          "expect_effects": [],
          "expect_data": {
            "suppressed_rows": 4
          },
          "expect_feedback": "the number of suppressed small cells is printed"
        },
        {
          "event": "EMIT_DONE",
          "input": {},
          "expect_state": "complete",
          "expect_effects": [],
          "expect_data": {
            "days_collected": 1
          },
          "expect_feedback": "the output path is printed"
        }
      ],
      "final_state": "complete",
      "final_data": {
        "hours_remaining": 10,
        "days_collected": 1,
        "active_request_id": null,
        "suppressed_rows": 4
      }
    },
    {
      "id": "TRACE-FAILURE",
      "kind": "failure-recovery",
      "initial_state": "idle",
      "fixtures": {
        "seed": 2,
        "initial_data": {},
        "provider_outcomes": [
          "error",
          "success"
        ]
      },
      "steps": [
        {
          "event": "RUN_REQUESTED",
          "input": {
            "request_id": "run-2-h0"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "hours_remaining": 12,
            "active_request_id": "run-2-h0"
          },
          "expect_feedback": "the run prints the date it is collecting"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-2-h0",
            "result_kind": "error"
          },
          "expect_state": "failed",
          "expect_effects": [],
          "expect_data": {
            "active_request_id": null
          },
          "expect_feedback": "the failing hour and its reason are printed, and no dataset file is written",
          "case": "error"
        },
        {
          "event": "RUN_REQUESTED",
          "input": {
            "request_id": "run-2-retry"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "hours_remaining": 12,
            "active_request_id": "run-2-retry"
          },
          "expect_feedback": "the run restarts and prints the date again"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-2-retry",
            "result_kind": "success"
          },
          "expect_state": "fetching",
          "expect_effects": [],
          "expect_data": {
            "hours_remaining": 11,
            "active_request_id": null
          },
          "expect_feedback": "the hour tag and its opened-PR count are printed",
          "case": "success"
        },
        {
          "event": "ALL_HOURS_DONE",
          "input": {},
          "expect_state": "aggregating",
          "expect_effects": [],
          "expect_data": {},
          "expect_feedback": "the run stops printing hours and begins counting"
        },
        {
          "event": "AGGREGATE_DONE",
          "input": {
            "suppressed_rows": 0
          },
          "expect_state": "emitting",
          "expect_effects": [],
          "expect_data": {
            "suppressed_rows": 0
          },
          "expect_feedback": "the number of suppressed small cells is printed"
        },
        {
          "event": "EMIT_DONE",
          "input": {},
          "expect_state": "complete",
          "expect_effects": [],
          "expect_data": {
            "days_collected": 1
          },
          "expect_feedback": "the output path is printed"
        }
      ],
      "final_state": "complete",
      "final_data": {
        "hours_remaining": 11,
        "days_collected": 1,
        "active_request_id": null,
        "suppressed_rows": 0
      }
    },
    {
      "id": "TRACE-SUSPEND",
      "kind": "suspend-resume",
      "initial_state": "idle",
      "fixtures": {
        "seed": 3,
        "initial_data": {},
        "provider_outcomes": [
          "success"
        ]
      },
      "steps": [
        {
          "event": "RUN_REQUESTED",
          "input": {
            "request_id": "run-3-h0"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "hours_remaining": 12,
            "active_request_id": "run-3-h0"
          },
          "expect_feedback": "the run prints the date it is collecting"
        },
        {
          "event": "RUN_INTERRUPTED",
          "input": {},
          "expect_state": "suspended",
          "expect_effects": [
            "E-CANCEL",
            "E-PERSIST"
          ],
          "expect_data": {
            "active_request_id": null
          },
          "expect_feedback": "the run reports how many hours it had already collected"
        },
        {
          "event": "RUN_RESUMED",
          "input": {
            "request_id": "run-3-h1"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-RESTORE"
          ],
          "expect_data": {
            "active_request_id": "run-3-h1"
          },
          "expect_feedback": "the run reports the hour it is resuming from"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-3-h1",
            "result_kind": "success"
          },
          "expect_state": "fetching",
          "expect_effects": [],
          "expect_data": {
            "hours_remaining": 11,
            "active_request_id": null
          },
          "expect_feedback": "the hour tag and its opened-PR count are printed",
          "case": "success"
        },
        {
          "event": "ALL_HOURS_DONE",
          "input": {},
          "expect_state": "aggregating",
          "expect_effects": [],
          "expect_data": {},
          "expect_feedback": "the run stops printing hours and begins counting"
        },
        {
          "event": "AGGREGATE_DONE",
          "input": {
            "suppressed_rows": 2
          },
          "expect_state": "emitting",
          "expect_effects": [],
          "expect_data": {
            "suppressed_rows": 2
          },
          "expect_feedback": "the number of suppressed small cells is printed"
        },
        {
          "event": "EMIT_DONE",
          "input": {},
          "expect_state": "complete",
          "expect_effects": [],
          "expect_data": {
            "days_collected": 1
          },
          "expect_feedback": "the output path is printed"
        }
      ],
      "final_state": "complete",
      "final_data": {
        "hours_remaining": 11,
        "days_collected": 1,
        "active_request_id": null,
        "suppressed_rows": 2
      }
    },
    {
      "id": "TRACE-EDGE",
      "kind": "edge",
      "initial_state": "idle",
      "fixtures": {
        "seed": 4,
        "initial_data": {},
        "provider_outcomes": [
          "stale",
          "empty",
          "timeout"
        ]
      },
      "steps": [
        {
          "event": "RUN_REQUESTED",
          "input": {
            "request_id": "run-4-h0"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "hours_remaining": 12,
            "active_request_id": "run-4-h0"
          },
          "expect_feedback": "the run prints the date it is collecting"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-4-orphan",
            "result_kind": "success"
          },
          "expect_state": "fetching",
          "expect_effects": [],
          "expect_data": {},
          "expect_feedback": "nothing is printed; the response is discarded",
          "case": "stale"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-4-h0",
            "result_kind": "empty"
          },
          "expect_state": "fetching",
          "expect_effects": [],
          "expect_data": {
            "hours_remaining": 11,
            "active_request_id": null
          },
          "expect_feedback": "the hour is printed as not published",
          "case": "empty"
        },
        {
          "event": "NEXT_HOUR",
          "input": {
            "request_id": "run-4-h1"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "active_request_id": "run-4-h1"
          },
          "expect_feedback": "the next hour tag is printed as it starts"
        },
        {
          "event": "HOUR_SETTLED",
          "input": {
            "request_id": "run-4-h1",
            "result_kind": "timeout"
          },
          "expect_state": "failed",
          "expect_effects": [],
          "expect_data": {
            "active_request_id": null
          },
          "expect_feedback": "the timed-out hour is printed, and no dataset file is written",
          "case": "timeout"
        }
      ],
      "final_state": "failed",
      "final_data": {
        "hours_remaining": 11,
        "days_collected": 0,
        "active_request_id": null,
        "suppressed_rows": 0
      }
    },
    {
      "id": "TRACE-DUPLICATE",
      "kind": "edge",
      "initial_state": "idle",
      "fixtures": {
        "seed": 5,
        "initial_data": {},
        "provider_outcomes": []
      },
      "steps": [
        {
          "event": "RUN_REQUESTED",
          "input": {
            "request_id": "run-5-h0"
          },
          "expect_state": "fetching",
          "expect_effects": [
            "E-FETCH"
          ],
          "expect_data": {
            "hours_remaining": 12,
            "active_request_id": "run-5-h0"
          },
          "expect_feedback": "the run prints the date it is collecting"
        },
        {
          "event": "RUN_REQUESTED",
          "input": {
            "request_id": "run-5-second"
          },
          "expect_state": "fetching",
          "expect_effects": [],
          "expect_data": {},
          "expect_feedback": "a run already owns the output path",
          "expect_disposition": "ignore"
        }
      ],
      "final_state": "fetching",
      "final_data": {
        "hours_remaining": 12,
        "days_collected": 0,
        "active_request_id": "run-5-h0",
        "suppressed_rows": 0
      }
    }
  ],
  "handoff": {
    "front_build_spec": {
      "motion_ids": [],
      "decorative_motion_ids": [],
      "owns": [
        "layout",
        "palette",
        "typography",
        "camera",
        "easing",
        "duration",
        "dpr",
        "lighting",
        "fallback styling"
      ]
    },
    "builder": {
      "contract": "canonical-json",
      "state_owner": "collector-reducer"
    },
    "remotion": {
      "trace_ids": [],
      "state_source": "not_applicable",
      "owns": "not_applicable"
    },
    "blender": {
      "asset_ids": []
    },
    "unity": {
      "disposition": "not_applicable",
      "reason": "no simulation runtime is needed"
    }
  },
  "open_decisions": []
}
```

## 6. Open decisions and handoff

None open. Approved by Felix on 2026-09-13; `logic_gate.py --handoff` passes.

- `front-build-spec` receives an empty semantic-motion set and owns only README/SVG visual constants.
- The builder is this repository itself; `collector-reducer` is `pr_fanout.cli.collect` plus `pr_fanout.metrics.Window`.
- **[UNVERIFIED]** whether GitHub treats bot/app account names as personal information. Natural persons are certainly covered. If contested, app logins drop to aggregates too.
