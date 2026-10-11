"""Testing interpreter: retain exact supplier input as uninterpreted observations."""

from ..core import models as m
from ..core.serialization import semantic_hash


class InputEchoTestInterpreter:
    def __init__(self, *, supplier_id: str):
        self.supplier_id = supplier_id

    async def interpret(
        self,
        context: m.NegotiationContext,
        conversation: m.ConversationView,
        previous_assessment: m.SupplierAssessment | None,
        budget: m.DecisionBudget,
    ) -> m.SupplierAssessment:
        observations = []
        for message in conversation.messages:
            if message.speaker != "supplier" or not message.body:
                continue
            span = m.MessageSpan(
                session_id=message.session_id,
                thread_id=message.thread_id,
                message_id=message.message_id,
                start=0,
                end=len(message.body),
                quote=message.body,
            )
            observations.append(
                m.GroundedObservation(
                    observation_id="sha256:" + semantic_hash(span),
                    kind="ambiguity",
                    dimension=None,
                    summary="Uninterpreted supplier input retained by testing component.",
                    citations=(span,),
                )
            )
        previous = previous_assessment
        result = m.SupplierAssessment(
            assessment_id="pending",
            supplier_id=self.supplier_id,
            snapshot=context.snapshot,
            revision=previous.revision + 1 if previous else 1,
            observations=tuple(observations),
            reported_constraints=(),
            hypotheses=(),
            uncertainties=(),
            questions=(),
            unknowns=("supplier preferences and approval authority are uninterpreted",),
            status="fallback",
            interpreter_id="input-echo-test-v1",
            model_call_id=None,
            parent_assessment_id=previous.assessment_id if previous else None,
        )
        return result.model_copy(
            update={
                "assessment_id": "sha256:"
                + semantic_hash(result.model_dump(mode="json", exclude={"assessment_id"}))
            }
        )


class DeterministicEvidencePreserver(InputEchoTestInterpreter):
    """Preserve trusted supplier spans without claiming semantic interpretation."""

    async def interpret(self, context, conversation, previous_assessment, budget):
        result = await super().interpret(context, conversation, previous_assessment, budget)
        result = result.model_copy(update={
            "status": "ok",
            "unknowns": ("supplier semantics, preferences and approval authority were not interpreted",),
            "interpreter_id": "deterministic-evidence-copy-v1",
        })
        return result.model_copy(update={"assessment_id": "sha256:" + semantic_hash(
            result.model_dump(mode="json", exclude={"assessment_id"})
        )})
