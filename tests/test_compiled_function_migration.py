from rdl_core import (
    ActiveCompiledMB,
    ActiveFunction,
    BoundaryContext,
    CompilationValidationStatus,
    CompiledFunction,
    CompiledMB,
    DeactivationStatus,
    FunctionDescription,
    PromotionDecisionStatus,
    RuptureObservationStatus,
    StructureCandidate,
    activate_compiled_replacement,
    activate_promoted_artifact,
    compile_function_candidate,
    evaluate_promotion,
    materialize_compiled_replacement,
    record_compilation_validation,
    record_deactivation,
    record_replacement_candidate,
    record_rupture_observation,
    record_supersession,
    request_recompilation,
)


def _compiled_function(version: str = "1"):
    context = BoundaryContext("compiled-function-migration")
    structure = StructureCandidate((), context)
    function = FunctionDescription("example.operator", version)
    candidate = compile_function_candidate(
        structure,
        function,
        purpose="migration contract",
    )
    validation = record_compilation_validation(
        candidate,
        CompilationValidationStatus.PASSED,
        context,
    )
    return context, candidate, CompiledFunction(function, structure, validation)


def _approved(artifact, candidate, context):
    rupture = record_rupture_observation(
        candidate,
        RuptureObservationStatus.NOT_DETECTED,
        context,
        check_id="durability",
    )
    decision = evaluate_promotion(
        artifact,
        context,
        ruptures=(rupture,),
        required_checks=("durability",),
    )
    assert decision.status == PromotionDecisionStatus.APPROVED
    return decision


def test_compiled_function_is_canonical_active_lifecycle_artifact():
    context, candidate, artifact = _compiled_function("1")
    decision = _approved(artifact, candidate, context)
    active = activate_promoted_artifact(decision, context)

    assert isinstance(artifact, CompiledFunction)
    assert isinstance(active, ActiveFunction)
    assert active.artifact is artifact
    # Historical name is a compatibility alias, not a second semantic kind.
    assert ActiveCompiledMB is ActiveFunction

    deactivation = record_deactivation(
        active,
        DeactivationStatus.DEACTIVATED,
        context,
        reason="bounded revision",
    )
    request = request_recompilation(
        active,
        deactivation,
        context,
        reason="bounded revision",
    )

    replacement_structure = StructureCandidate((), context)
    replacement = record_replacement_candidate(
        request,
        replacement_structure,
        FunctionDescription("example.operator", "2"),
    )
    replacement_validation = record_compilation_validation(
        replacement.candidate,
        CompilationValidationStatus.PASSED,
        context,
    )
    compiled_replacement = materialize_compiled_replacement(
        replacement,
        replacement_validation,
    )

    assert isinstance(compiled_replacement.compiled, CompiledFunction)
    assert compiled_replacement.compiled.function.version == "2"

    replacement_decision = _approved(
        compiled_replacement.compiled,
        replacement.candidate,
        context,
    )
    active_v2 = activate_compiled_replacement(
        compiled_replacement,
        replacement_decision,
        context,
    )
    record = record_supersession(
        active,
        active_v2,
        compiled_replacement,
        context,
    )
    assert record.predecessor is active
    assert record.replacement is active_v2


def test_legacy_compiled_mb_remains_accepted_during_migration():
    context, candidate, canonical = _compiled_function("1")
    legacy = canonical.to_legacy()

    assert isinstance(legacy, CompiledMB)
    decision = _approved(legacy, candidate, context)
    active = activate_promoted_artifact(decision, context)

    assert isinstance(active, ActiveFunction)
    assert active.artifact is legacy
    assert CompiledFunction.from_legacy(legacy) == canonical
