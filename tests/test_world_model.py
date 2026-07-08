from runtime.world import WorldModel


def test_world_model_is_stale_until_updated() -> None:
    world = WorldModel()

    assert world.stale
    snapshot = world.update({"active_window": "Editor"})

    assert not world.stale
    assert snapshot.data["active_window"] == "Editor"

    world.mark_stale()
    assert world.stale
