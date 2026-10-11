"""Conservative attributed fallback; no commercial inference or economic authority."""

from ..core import models as m
from ..core.serialization import semantic_hash
from .testing import InputEchoTestInterpreter


async def fallback(context, conversation, previous, budget, supplier_id, cause, call_id):
    assessment = await InputEchoTestInterpreter(supplier_id=supplier_id).interpret(
        context, conversation, previous, budget,
    )
    assessment = m.SupplierAssessment.model_validate({
        **assessment.model_dump(), "interpreter_id": "grounded-interpreter-v1", "model_call_id": call_id,
        "unknowns": ("supplier interpretation unavailable", cause),
    })
    return assessment.model_copy(update={
        "assessment_id": "sha256:" + semantic_hash(assessment.model_dump(mode="json", exclude={"assessment_id"})),
    })
