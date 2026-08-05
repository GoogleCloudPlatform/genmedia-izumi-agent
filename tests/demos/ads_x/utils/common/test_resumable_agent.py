"""Guards the workaround for ADK's one-resume-per-invocation bug.

A run with three review checkpoints has to be resumable three times. Stock ADK
allows one: a transferring LlmAgent marks itself finished even when the agent it
resumed paused again, after which every resume is a silent no-op.

If these fail after an ADK upgrade, check whether upstream fixed the bug — if it
has, ResumableLlmAgent can be deleted and root_agent reverted to LlmAgent.
"""

import inspect

from google.adk.agents.llm_agent import LlmAgent

from demos.backend.ads_x.utils.common.resumable_agent import ResumableLlmAgent


def test_the_upstream_bug_is_still_there():
    """The workaround exists for a reason; assert the reason still holds."""
    source = inspect.getsource(LlmAgent._run_async_impl)
    resume_branch = source.split("should_pause = False")[0]

    assert (
        "_get_subagent_to_resume" in resume_branch
    ), "ADK's resume branch has changed shape; re-check the workaround."
    assert "end_of_agent=True" in resume_branch, "ADK resume branch changed shape."
    # The bug: no pause check before declaring the agent finished.
    assert "should_pause" not in resume_branch, (
        "ADK's resume branch now checks for a pause - the upstream bug may be "
        "fixed. Verify with scripts/spikes/repro_multi_gate_resume.py and, if "
        "so, delete ResumableLlmAgent and use a plain LlmAgent."
    )


def test_the_subclass_adds_the_missing_check():
    source = inspect.getsource(ResumableLlmAgent._run_async_impl)
    resume_branch = source.split("# Unchanged from ADK below")[0]

    assert "should_pause_invocation" in resume_branch
    assert "paused_again" in resume_branch


def test_it_is_otherwise_an_llm_agent():
    assert issubclass(ResumableLlmAgent, LlmAgent)


def test_the_root_agent_uses_it():
    # The bug only bites the transferring root, which is where it must apply.
    # Imported the way agent.py does: the package is reachable as both
    # `ads_x...` and `demos.backend.ads_x...`, which are distinct class objects.
    from ads_x.agent import root_agent
    from ads_x.utils.common.resumable_agent import (
        ResumableLlmAgent as RuntimeResumableLlmAgent,
    )

    assert isinstance(root_agent, RuntimeResumableLlmAgent)
