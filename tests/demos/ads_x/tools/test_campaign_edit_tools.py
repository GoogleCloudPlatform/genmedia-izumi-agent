"""Tests for correcting the campaign brief at the strategy checkpoint."""

from types import SimpleNamespace

from demos.backend.ads_x.tools.parameters import campaign_edit_tools


def _ctx(params=None, **extra):
    state = {"parameters": dict(params or {"campaign_name": "Aurora"})}
    state.update(extra)
    return SimpleNamespace(state=state, actions=SimpleNamespace(escalate=None))


async def test_shows_the_brief_with_look_and_assets():
    ctx = _ctx(
        {"campaign_name": "Aurora", "target_audience": "urban professionals"},
        master_production_recipe={"look_name": "Luxury Heritage"},
        user_assets={"bottle.png": {}},
    )
    payload = (await campaign_edit_tools.show_campaign_parameters(ctx))["result"]

    assert payload["parameters"]["campaign_name"] == "Aurora"
    assert payload["look"] == "Luxury Heritage"
    assert payload["uploaded_assets"] == ["bottle.png"]
    assert "target_audience" in payload["editable_fields"]


async def test_editing_a_field_reports_the_change():
    ctx = _ctx({"target_audience": "everyone"})
    result = await campaign_edit_tools.edit_campaign_parameter(
        ctx, "target_audience", "urban cyclists"
    )

    assert result["status"] == "succeeded"
    assert ctx.state["parameters"]["target_audience"] == "urban cyclists"
    assert "everyone" in result["result"]


async def test_only_whitelisted_fields_are_editable():
    # Structural state must not be reachable through this door.
    result = await campaign_edit_tools.edit_campaign_parameter(
        _ctx(), "template_name", "Custom"
    )
    assert result["status"] == "failed"


async def test_edit_requires_a_value_and_existing_parameters():
    assert (await campaign_edit_tools.edit_campaign_parameter(_ctx(), "vertical", " "))[
        "status"
    ] == "failed"
    empty = SimpleNamespace(state={}, actions=SimpleNamespace(escalate=None))
    assert (
        await campaign_edit_tools.edit_campaign_parameter(empty, "vertical", "Retail")
    )["status"] == "failed"


async def test_turning_the_virtual_creator_on_records_the_description():
    ctx = _ctx()
    result = await campaign_edit_tools.set_virtual_creator(
        ctx, True, "a calm woman in her 30s"
    )

    assert ctx.state["parameters"]["generate_virtual_creator"] is True
    assert ctx.state["parameters"]["creator_description"] == "a calm woman in her 30s"
    assert "person" in result["result"]


async def test_turning_it_off_makes_the_ad_product_only():
    ctx = _ctx({"generate_virtual_creator": True})
    result = await campaign_edit_tools.set_virtual_creator(ctx, False)

    assert ctx.state["parameters"]["generate_virtual_creator"] is False
    assert "product-only" in result["result"]
