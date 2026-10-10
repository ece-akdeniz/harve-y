"""Reconcile rejected alternative-sheet acceptance against authoritative state."""

from arena_kit.client import ArenaError
from arena_kit.cost import must_haves_ok
from arena_kit.docs import standard_terms
from arena_kit.play import RemoteTable, fetch_documents, latest

from .optimizer import alternative_cost


class GuardedRemoteTable(RemoteTable):
    def __init__(self, client, agent, case=None):
        super().__init__(client, case)
        self.agent = agent

    def open(self, case_id):
        case, threads = super().open(case_id)
        self.case = case
        return case, threads

    def close(self, supplier_id, message):
        try:
            return super().close(supplier_id, message)
        except ArenaError as error:
            action = message.get('action') or {}
            if error.status != 422 or action.get('type') != 'accept':
                raise
            state = self.client.session(self.session_id)
            if state.get('status') == 'ended':
                return state.get('result') or self.result()
            thread = state.get('threads', {}).get(supplier_id) or {}
            current_id = thread.get('offer_id')
            if not current_id or current_id == action.get('term_sheet_id') or thread.get('closed'):
                raise
            events = self.client.thread(self.session_id, supplier_id)['messages']
            for event in events:
                fetch_documents(self, event)
            reply = latest(events)
            if reply.get('status') not in {'open', 'final_offer', 'agreed'}:
                raise
            sheet = next((s for s in reply.get('term_sheets') or [] if s['term_sheet_id'] == current_id), None)
            std = standard_terms(events)
            if not sheet or not must_haves_ok(self.case, sheet['terms'], std):
                raise
            cost = self.agent._cost(self.case, supplier_id, sheet['terms'], std)
            if cost >= alternative_cost(self.case):
                raise
            self.agent._log(self.case, 'accept_reconciled', supplier_id,
                            rejected_sheet=action['term_sheet_id'], sheet=current_id, c=cost)
            # New logical action, not a retry of the rejected alternative payload.
            return super().close(supplier_id, {'action': {'type': 'accept', 'term_sheet_id': current_id}})
