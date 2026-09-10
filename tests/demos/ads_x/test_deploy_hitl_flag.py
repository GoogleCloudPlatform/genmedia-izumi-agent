"""The review-checkpoint flag has to survive the trip to the deployed agent."""

import re


def test_agent_engine_deploy_forwards_the_flag():
    """Agent Engine takes a hardcoded env allowlist.

    A variable missing from it is simply not set on the deployed agent, so the
    checkpoints would be off no matter what the deployer exported - and off is
    indistinguishable from working, since the pipeline just runs straight
    through.
    """
    source = open("scripts/deploy_to_agent_platform.py").read()
    env_block = source[source.index("env_vars = {") : source.index("# Vertex Agent")]
    assert "ENABLE_HITL_GATES" in env_block


def test_it_defaults_to_off_when_unset():
    source = open("scripts/deploy_to_agent_platform.py").read()
    match = re.search(r'"ENABLE_HITL_GATES":\s*os\.getenv\([^)]*\)', source)
    assert match, "expected the flag to be read from the environment"
    assert '"False"' in match.group(), "a deploy that does not ask must get no gates"
