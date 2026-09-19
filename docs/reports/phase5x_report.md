# Phase5.x — Requirement Quality Hardening

IN PROGRESS. Phase5remote d6e39c8 gate후진행한다. 120 synthetic examples를40development/80heldout로고정하고gold는AUTO-GENERATED / NOT HUMAN VERIFIED로표시한다. Promptv3/modelrevision/contract를첫heldout호출전에freeze한다. 공개seed20은development에만둔다. source의조건/부정/targetexclusion/숫자/장문/미지원subset을검증하며결과를본뒤gold를조용히수정하지않는다.

기존criticalFP(비실행gold→READY)와지원gold의잘못된target/axis이동을분리해보고한다. Dataset/prompt최적화의영향과동일case3회의상관을명시하고사람검수표를별도로제공한다. GPU3만현재guard예산으로사용하며listenercheck/원격checkpoint와선행215regression을유지한다.
