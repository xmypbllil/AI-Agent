from runtime.backends import BackendCapabilities, BackendCandidate, BackendManager, BackendRole
from runtime.observations import (
    ObservationKind,
    ObservationQuery,
    ObservationResult,
    ProcessIdentity,
    ProcessObservation,
)
from runtime.observations.engine import ObservationExecutor
from runtime.world import WorldModel


class FakeObservationBackend:
    @property
    def name(self) -> str:
        return "fake-observer"

    @property
    def role(self) -> BackendRole:
        return BackendRole.MOCK

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_processes=True)

    def score_observation(self, query: ObservationQuery, context=None):
        return BackendCandidate(
            backend_name=self.name,
            score=0.6,
            reason="test observer supports process list",
        )

    def observe(self, query: ObservationQuery) -> ObservationResult:
        return ObservationResult(
            query_id=query.query_id,
            backend_used=self.name,
            backend_score=0.6,
            backend_reason="test observer supports process list",
            observations=(
                ProcessObservation(identity=ProcessIdentity(pid=1, name="init")),
            ),
        )


def test_observation_executor_updates_world_model() -> None:
    world = WorldModel()
    executor = ObservationExecutor(
        backend_manager=BackendManager(observation_backends=[FakeObservationBackend()]),
        world=world,
    )

    result = executor.observe(ObservationQuery(ObservationKind.PROCESS_LIST))

    assert result.backend_used == "fake-observer"
    assert not world.stale
    assert world.snapshot.data["processes"][0].identity.name == "init"
