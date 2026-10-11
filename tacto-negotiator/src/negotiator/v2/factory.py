"""Focused offline composition entry; full runtime/factory acceptance remains incomplete."""


from .adapters.model import AsyncModelGateway
from .adapters.official import OfficialArithmetic
from .adapters.offline import OfflineContextAssembler, OfflineRecordedInputs, load_recorded_json
from .core.serialization import canonical_json
from .economics.estimates import SourceCostEstimateBuilder
from .economics.finite import SuppliedCandidateGenerator
from .economics.official import OfficialEconomicEvaluator
from .evidence.claims import EvidenceProjections
from .evidence.context import LayeredContextBuilder
from .execution.render import TemplateActionRenderer
from .execution.validation import FinalActionValidator, payload_bytes
from .intelligence.interpreter import GroundedInterpreter, InterpreterConfig, project
from .intelligence.testing import DeterministicEvidencePreserver, InputEchoTestInterpreter
from .orchestration.offline import OfflineDecisionCoordinator, OfflineDecisionTrace
from .strategy.selection import BoundedModelSelector, SelectorConfig
from .strategy.testing import MinimumCostTestSelector, SuppliedIntentTestPolicy


async def run_recorded_decision(
    inputs: OfflineRecordedInputs,
    *,
    assembler: OfflineContextAssembler,
    coordinator: OfflineDecisionCoordinator,
) -> OfflineDecisionTrace:
    inputs = load_recorded_json(inputs.model_dump_json())
    snapshot = assembler.assemble(inputs)
    return await coordinator.run_once(
        snapshot, previous_assessment=inputs.previous_assessment, recorded_input_bytes=canonical_json(inputs)
    )


def bounded_services(inputs, clock, transport=None, config=None, *, prompt_revision="v1", arm="grounded"):
    """Same bounded ports for recorded inputs and the local Lab bridge."""
    evaluator = OfficialEconomicEvaluator(oracle=OfficialArithmetic())
    from .evidence.resolver import LayeredEvidenceResolver

    assembler = OfflineContextAssembler(
        context_builder=LayeredContextBuilder(resolver=LayeredEvidenceResolver(admit_live_quotes=True)),
        projections=EvidenceProjections(),
        estimate_builder=SourceCostEstimateBuilder(),
    )
    supplier = inputs.target_supplier_id
    interpreter = InputEchoTestInterpreter(supplier_id=supplier)
    selector = MinimumCostTestSelector()
    proposal = SuppliedIntentTestPolicy(supplier_id=supplier, include_question=True)
    generator = SuppliedCandidateGenerator(packages=inputs.packages)
    if transport is not None:
        gateway = AsyncModelGateway(transport=transport)
        hashes = tuple(msg.content_hash for msg in inputs.server.threads[0].conversation.messages)
        ic = InterpreterConfig(
            provider_id=config.provider_id,
            protocol_id=config.protocol_id,
            model_id=config.model_id,
            prompt_version="grounded-supplier-" + prompt_revision,
            task_schema_version="assessment-citation-ids-v1" if prompt_revision == "v3" else "assessment-draft-v1",
            max_tokens=98304 if arm == "adaptive" else 16384,
            time_limit_s=inputs.budget.model_time_limit_s,
            approved_message_hashes=hashes,
            max_input_chars=64000 if prompt_revision == "v3" else 16000,
        )
        sc = SelectorConfig(
            **{
                **ic.model_dump(),
                "prompt_version": "grounded-selection-" + ("v2" if prompt_revision == "v3" else prompt_revision),
                "task_schema_version": "selector-response-v1",
                "time_limit_s": inputs.budget.model_time_limit_s,
                "full_observations": prompt_revision == "v3",
                "max_input_chars": 64000 if prompt_revision == "v3" else 16000,
            }
        )
        if arm == "adaptive":
            interpreter = DeterministicEvidencePreserver(supplier_id=supplier)
        elif arm == "grounded":
            interpreter = GroundedInterpreter(model=gateway, clock=clock, config=ic)
        selector = BoundedModelSelector(model=gateway, clock=clock, config=sc)
        if arm == "adaptive":
            from .strategy.proposal import BoundedProposalPolicy, ProposalSelector, ProposedCandidateGenerator
            proposal = BoundedProposalPolicy(model=gateway, clock=clock, config=ic, evaluator=evaluator,
                                             projector=project)
            generator = ProposedCandidateGenerator(fallback=generator)
            selector = ProposalSelector()
    coordinator = OfflineDecisionCoordinator(
        interpreter=interpreter,
        proposal=proposal,
        generator=generator,
        evaluator=evaluator,
        selector=selector,
        renderer_factory=lambda batch: TemplateActionRenderer(batch=batch),
        validator=FinalActionValidator(evaluator=evaluator, clock=clock),
        payload_encoder=payload_bytes,
        clock=clock,
        model_token_limit=(196608 if arm == "adaptive" else 32768) if transport is not None else None,
    )
    return assembler, coordinator



def local_lab_agent(*, dataset_path, trace_root, arm="grounded", clock=None, transport=None,
                    closing_authority=False, model_config=None):
    """Explicit opt-in local Lab composition; remote execution remains unavailable."""
    from .adapters.lab import LocalV2LabAgent
    from .orchestration.metrics import decision_metrics

    return LocalV2LabAgent(dataset_path=dataset_path, trace_root=trace_root, arm=arm,
                           clock=clock, transport=transport, runtime_builder=bounded_services,
                           run_decision=run_recorded_decision, metrics=decision_metrics,
                           closing_authority=closing_authority, model_config=model_config)


def online_lab_agent(*, dataset_path, trace_root, transport, model_config, execution_allowance, clock=None):
    """Explicitly approved P10 composition for the existing tracked Lab runner only."""
    from .adapters.online import VerifiedOnlineV2LabAgent
    from .orchestration.metrics import decision_metrics

    return VerifiedOnlineV2LabAgent(dataset_path=dataset_path, trace_root=trace_root, arm="adaptive",
        transport=transport, model_config=model_config, execution_allowance=execution_allowance, clock=clock,
        runtime_builder=bounded_services, run_decision=run_recorded_decision, metrics=decision_metrics)
