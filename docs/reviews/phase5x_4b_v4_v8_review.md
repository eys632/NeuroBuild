# 4B v4 failure and bounded v8 review

AUTO-GENERATED / NOT HUMAN VERIFIED. Independent AI review is not human ground truth.

The root replayed the complete summary for run `20260919T223253Z-6038073ec36044adb6251920c5d6b285`. Schema/parser40, semantic34, rawFP1, unsafeaccepted3 and FN3 match the archived results. The independent architecture reviewer compared failures against 4B/v3: HD-B01 improved; E01, F02, HD-A02 and HD-I02 regressed; HD-F01/02 remained failures (HD-F02 changed failure type). V4 already contains condition and preservation instructions, so missing rules alone do not explain these observed failures.

V8 retains the exact v3 bytes and appends only two general reminders after the examples. They define target_text as the full source selection phrase, including location and exclusions, and distinguish explicit axis direction from an unsigned magnitude. No dataset sentence is copied into the additions. Prompt authoring is informed by development errors, not blind evaluation.

The independent reviewer checked the concrete draft and found the rules consistent with the existing contract. Four independent signed-Y examples passed the unchanged CPU parser. The reviewer identified that 'one requested axis is a complete movement' was too broad; the final sentence now says that if the requested axis has direction, distance and unit, the other axis is unnecessary and remains null. External conditions and missing information still use the original v3 rules.

The separate CPU tokenizer check in [the candidate review](../instruction_model_reassessment.md) records the final prompt hash and full input/output window bounds. Existing schema, parser, scorer, model, sampling, runtime and gold remain unchanged. This review authorizes no quality claim: all40 development cases must be evaluated, and a successful diagnostic still requires the separate40×3 formal run before any holdout inference.

Runtime read-only review found the current 4B epoch consistent with its archived launch and guard: estimated16384MiB plus7275MiB margin fits36373MiB free; minimum observed free26864MiB remained above the floor, and its own log contained no OOM/CUDA/inference failure. Aggregate baseline-relative rise9510MiB is not a guaranteed per-process peak. GPU3 only and archived five loopback TCP listeners remain the verified launch scope.
