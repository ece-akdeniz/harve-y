"""Scripted port doubles: return supplied typed artifacts; no negotiation algorithms."""

from datetime import datetime, timedelta


class FakeClock:
    def __init__(self, now="2026-10-10T10:00:00+00:00"):
        self.now = datetime.fromisoformat(now)
        self.elapsed = 0.0

    def utcnow(self):
        return self.now

    def advance(self, seconds):
        self.now += timedelta(seconds=seconds)
        self.elapsed += seconds

    def monotonic(self):
        return self.elapsed


class ReplayModelGateway:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def complete(self, request, budget):
        self.calls.append((request, budget))
        if isinstance(self.result, Exception):
            raise self.result
        if hasattr(self.result, "model_copy") and hasattr(request, "call_id") and hasattr(self.result, "call_id"):
            # A provider adapter attributes the scripted raw response to this trusted request;
            # it doesn't let the response invent another call's identity.
            return self.result.model_copy(update={"call_id": request.call_id})
        return self.result


class ReplayArenaGateway:
    def __init__(self, observations=(), results=()):
        self.observations = list(observations)
        self.results = list(results)
        self.submissions = []

    async def observe(self, session_id, budget):
        return self.observations.pop(0)

    async def submit(self, operation, budget):
        self.submissions.append(operation)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    async def fetch_document(self, session_id, attachment_id, budget):
        raise AssertionError("No document read scripted for this fixture")


class ScriptedPipeline:
    """One object supplies narrow ports for M1 wiring; every method records its inputs."""

    def __init__(self, artifacts):
        self.artifacts = artifacts
        self.calls = []

    def _return(self, stage, args):
        self.calls.append((stage, args))
        return self.artifacts[stage]

    def build_context(self, prepared, case, server, documents, as_of):
        return self._return("context", (prepared, case, server, documents, as_of))

    async def interpret(self, context, conversation, previous_assessment, budget):
        return self._return("assessment", (context, conversation, previous_assessment, budget))

    async def propose_strategies(self, context, assessment, state, budget, research):
        return self._return("intents", (context, assessment, state, budget, research))

    def generate_candidates(self, intent, context, state, budget):
        return self._return("generation", (intent, context, state, budget))

    def evaluate_candidates(self, candidates, context):
        return self._return("evaluations", (candidates, context))

    async def select_action(self, candidates, assessment, state, budget, research):
        return self._return("decision", (candidates, assessment, state, budget, research))

    def render(self, decision, selected, claims, context):
        return self._return("rendered", (decision, selected, claims, context))

    def validate_action(self, action, context, state, budget):
        return self._return("validation", (action, context, state, budget))

    async def execute_action(self, action, permit, operation, budget):
        return self._return("execution", (action, permit, operation, budget))

    def process_feedback(self, previous_state, operation, response):
        return self._return("feedback", (previous_state, operation, response))

    def evaluate_package(self, package, supplier_id, context):
        return self._return("package_evaluation", (package, supplier_id, context))

    def evaluate(self, case, terms, supplier):
        return self._return("official_cost", (case, terms, supplier))

    async def evaluate_intents(self, intents, budget):
        return self._return("research_evaluations", (intents, budget))

    def decide_close(self, context, state, reason_code):
        return self._return("close", (context, state, reason_code))

    def verify(self, candidate, evidence, recipient_id, usage):
        return self._return("claim", (candidate, evidence, recipient_id, usage))

    def apply_event(self, state, event):
        return self._return("state", (state, event))

    async def decide(self, snapshot):
        return self._return("outcome", (snapshot,))

    async def load_state(self, run_id, case_id):
        return self._return("loaded_state", (run_id, case_id))

    async def persist_state(self, expected_version, commit):
        return self._return("commit", (expected_version, commit))

    async def append_observations(self, expected_version, events):
        return self._return("observations", (expected_version, events))

    async def pending_operations(self, run_id):
        return self._return("pending_operations", (run_id,))

    async def reconcile(self, operation, context, state, budget):
        return self._return("reconciliation", (operation, context, state, budget))
