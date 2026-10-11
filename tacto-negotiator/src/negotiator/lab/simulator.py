"""Local client seam around the existing official contract simulator; no HTTP or model calls."""

from arena_kit.sim import Sim


class InProcessSimulatorClient:
    """Existing official simulator through the same client methods RecordingTable consumes."""

    def __init__(self, case):
        self.sim = Sim({case["case_id"]: case}, no_clock=False)
        self.team = "local-fixture-team"
        self.sim.teams[self.team] = "local-v2-integration"

    def cases(self, set_):
        if set_ != "practice":
            raise ValueError("local simulator supports practice-shaped fixtures only")
        return [{**c, "hosted": True} for c in self.sim.cases.values()]

    def me(self):
        return {"practice": self.sim.practice(self.team)}

    def open_session(self, case_id):
        return self.sim.open(self.team, case_id)

    def send_message(self, session_id, supplier_id, message):
        return self.sim.message(self.team, session_id, supplier_id, message)

    def session(self, session_id):
        return self.sim.state(self.team, session_id)

    def thread(self, session_id, supplier_id):
        return self.sim.thread(self.team, session_id, supplier_id)

    def attachment(self, session_id, attachment_id):
        return self.sim.attachment(self.team, session_id, attachment_id)[0]

