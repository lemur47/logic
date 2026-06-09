"""
MCP server v0.1 tests.

Covers: registration of exactly the four classic tools (each leading with a
decision question), one worked example per tool through the shared Pydantic
models, seed-42 determinism on the stochastic tool, and the structured-error
contract (typed tags, no tracebacks on the wire).

Implementation-grade maths sweeps live in tests/{pert,montecarlo,tco,evm}/ —
we do not duplicate them here. `estimate_from_history` is parked for v0.1
(see the banner in mcp_server/tools.py) and is intentionally untested here.
"""

import pytest
from mcp.server.fastmcp.exceptions import ToolError as FastMCPToolError
from pydantic import ValidationError as PydanticValidationError

from app.evm.schemas import EvmCalculateInput, EvmCalculateResponse
from app.montecarlo.schemas import SimulationConfig, SimulationResult
from app.montecarlo.schemas import TaskInput as MCTaskInput
from app.pert.schemas import TagInput, TaskEstimation
from app.pert.schemas import TaskInput as PertTaskInput
from app.tco.schemas import CompareOption, CompareRequest, CompareResponse
from mcp_server.errors import (
    ToolComputationError,
    ToolInternalError,
    ToolValidationError,
    structured_errors,
)
from mcp_server.server import mcp
from mcp_server.tools import (
    compare_investment_options,
    estimate_task_duration,
    evaluate_project_health,
    identify_schedule_risk,
)

V01_TOOLS = {
    "estimate_task_duration",
    "identify_schedule_risk",
    "compare_investment_options",
    "evaluate_project_health",
}


# =============================================================================
# Registration
# =============================================================================


class TestServerRegistration:
    async def test_exactly_the_four_v01_tools_registered(self):
        names = {t.name for t in await mcp.list_tools()}
        assert names == V01_TOOLS

    async def test_parked_flagship_is_not_registered(self):
        names = {t.name for t in await mcp.list_tools()}
        assert "estimate_from_history" not in names

    async def test_descriptions_lead_with_decision_question(self):
        """Each tool's description states a 'Use when:' decision question so the
        LLM picks the right tool by purpose, not by acronym."""
        for tool in await mcp.list_tools():
            assert tool.description, f"Tool {tool.name} has no description"
            assert "Use when:" in tool.description, (
                f"Tool {tool.name} description should state a 'Use when:' question"
            )

    async def test_every_tool_exposes_input_and_output_schema(self):
        """Inputs and outputs are the shared FastAPI Pydantic models, so every
        tool carries both an input and a structured output schema."""
        for tool in await mcp.list_tools():
            assert tool.inputSchema.get("properties"), f"{tool.name} has no input properties"
            assert tool.outputSchema is not None, f"{tool.name} has no output schema"


# =============================================================================
# estimate_task_duration (PERT)
# =============================================================================


class TestEstimateTaskDuration:
    def test_textbook_worked_example(self):
        result = estimate_task_duration(PertTaskInput(optimistic=2, most_likely=5, pessimistic=14))
        assert isinstance(result, TaskEstimation)
        assert result.textbook.expected == pytest.approx(6.0)  # (2 + 4*5 + 14) / 6
        assert result.textbook.std_dev == pytest.approx(2.0)  # (14 - 2) / 6
        assert result.adjusted is None

    def test_insight_tag_widens_the_pessimistic_tail(self):
        result = estimate_task_duration(
            PertTaskInput(
                optimistic=2,
                most_likely=5,
                pessimistic=14,
                tags=[TagInput(name="FRAGMENTED_COMMUNICATION", severity=0.5)],
            )
        )
        assert result.adjusted is not None
        assert result.adjusted.expected > result.textbook.expected

    def test_optimistic_exceeding_most_likely_is_a_computation_error(self):
        with pytest.raises(ToolComputationError, match=r"\[ComputationError\]"):
            estimate_task_duration(PertTaskInput(optimistic=10, most_likely=5, pessimistic=14))

    def test_unknown_insight_tag_is_a_validation_error(self):
        with pytest.raises(ToolValidationError, match="Unknown insight tag"):
            estimate_task_duration(
                PertTaskInput(
                    optimistic=2,
                    most_likely=5,
                    pessimistic=14,
                    tags=[TagInput(name="nonesuch", severity=0.5)],
                )
            )


# =============================================================================
# identify_schedule_risk (Monte Carlo schedule)
# =============================================================================


class TestIdentifyScheduleRisk:
    # A simple linear chain: Design → Build → Test.
    WORKED = [
        MCTaskInput(name="Design", optimistic=3, most_likely=5, pessimistic=10),
        MCTaskInput(
            name="Build", optimistic=8, most_likely=14, pessimistic=25, depends_on=["Design"]
        ),
        MCTaskInput(name="Test", optimistic=3, most_likely=5, pessimistic=10, depends_on=["Build"]),
    ]

    def test_seed_42_is_reproducible(self):
        a = identify_schedule_risk(self.WORKED, SimulationConfig(num_simulations=2000, seed=42))
        b = identify_schedule_risk(self.WORKED, SimulationConfig(num_simulations=2000, seed=42))
        assert a.percentiles.model_dump() == b.percentiles.model_dump()

    def test_default_seed_equals_explicit_42(self):
        """An omitted seed defaults to 42, so the default run matches seed=42."""
        default = identify_schedule_risk(self.WORKED, SimulationConfig(num_simulations=2000))
        explicit = identify_schedule_risk(
            self.WORKED, SimulationConfig(num_simulations=2000, seed=42)
        )
        assert default.percentiles.model_dump() == explicit.percentiles.model_dump()

    def test_worked_example_pins_output(self):
        result = identify_schedule_risk(
            self.WORKED, SimulationConfig(num_simulations=2000, seed=42)
        )
        assert isinstance(result, SimulationResult)
        # Pinned reference run (seed 42, 2,000 iterations) — guards against regressions.
        assert abs(result.percentiles.P50 - 25.53) < 0.01
        assert abs(result.percentiles.P85 - 29.62) < 0.01
        # In a strict linear chain every task is always on the critical path.
        assert result.critical_path_frequency == {"Design": 1.0, "Build": 1.0, "Test": 1.0}

    def test_empty_task_list_is_a_validation_error(self):
        with pytest.raises(ToolValidationError, match="at least one task"):
            identify_schedule_risk([])

    # Parallel oracle: A and B run concurrently, C merges them (depends_on A & B).
    # Honoured deps  -> makespan = max(A, B) + C, and exactly one of A/B is on the
    #                   critical path per run, so freq(A) + freq(B) == 1.0, both < 1.
    # Dropped deps   -> sequential fallback sums all three: makespan = A + B + C,
    #                   and every task is critical (freq 1.0 each).
    # A 3-task *chain* cannot tell these apart (chain == sequential arithmetic), so
    # this merge structure is what actually exercises depends_on through the tool.
    PARALLEL = [
        MCTaskInput(name="A", optimistic=2, most_likely=4, pessimistic=6),
        MCTaskInput(name="B", optimistic=1, most_likely=3, pessimistic=8),
        MCTaskInput(name="C", optimistic=3, most_likely=5, pessimistic=9, depends_on=["A", "B"]),
    ]

    def test_parallel_network_is_not_summed_through_the_tool(self):
        """The tool honours depends_on: a parallel merge is solved as max-of-paths,
        not a blind sum. Guards against the adapter dropping deps and collapsing
        every call to the sequential fallback."""
        cfg = SimulationConfig(num_simulations=5000, seed=42)
        parallel = identify_schedule_risk(self.PARALLEL, cfg)

        # Same three tasks with the dependency stripped -> sequential fallback.
        bare = [
            MCTaskInput(
                name=t.name,
                optimistic=t.optimistic,
                most_likely=t.most_likely,
                pessimistic=t.pessimistic,
            )
            for t in self.PARALLEL
        ]
        sequential = identify_schedule_risk(bare, cfg)

        cpf = parallel.critical_path_frequency
        # The merge task C is always on the critical path; A and B split it, never
        # both fully critical — the signature of honoured parallelism.
        assert cpf["C"] == pytest.approx(1.0)
        assert 0.0 < cpf["A"] < 1.0
        assert 0.0 < cpf["B"] < 1.0
        assert cpf["A"] + cpf["B"] == pytest.approx(1.0)

        # max(A, B) + C is strictly cheaper than A + B + C: parallelism shortens
        # the schedule. If deps were dropped these would be equal.
        assert parallel.mean < sequential.mean
        assert sequential.critical_path_frequency == {"A": 1.0, "B": 1.0, "C": 1.0}


# =============================================================================
# compare_investment_options (TCO)
# =============================================================================


class TestCompareInvestmentOptions:
    def test_worked_example_ranks_by_lifetime_cost(self):
        result = compare_investment_options(
            CompareRequest(
                options=[
                    CompareOption(
                        name="Cloud",
                        initial_price=5000,
                        useful_life_years=3,
                        annual_operating_cost=12000,
                    ),
                    CompareOption(
                        name="On-prem",
                        initial_price=40000,
                        useful_life_years=3,
                        annual_maintenance=3000,
                    ),
                ]
            )
        )
        assert isinstance(result, CompareResponse)
        assert result.best_option == "Cloud"
        assert result.results[0].rank == 1
        assert result.results[0].annual_cost <= result.results[1].annual_cost

    def test_fewer_than_two_options_rejected_by_shared_schema(self):
        with pytest.raises(PydanticValidationError):
            CompareRequest(
                options=[CompareOption(name="A", initial_price=100, useful_life_years=1)]
            )


# =============================================================================
# evaluate_project_health (EVM)
# =============================================================================


class TestEvaluateProjectHealth:
    def test_off_track_worked_example(self):
        result = evaluate_project_health(EvmCalculateInput(pv=1000, ev=900, ac=1100, bac=5000))
        assert isinstance(result, EvmCalculateResponse)
        assert result.health.status == "off_track"
        assert result.metrics.spi == pytest.approx(0.9)
        assert result.metrics.cpi is not None and result.metrics.cpi < 1.0

    def test_on_track_worked_example(self):
        result = evaluate_project_health(EvmCalculateInput(pv=1000, ev=1000, ac=950, bac=5000))
        assert result.health.status == "on_track"

    def test_zero_budget_rejected_by_shared_schema(self):
        with pytest.raises(PydanticValidationError):
            EvmCalculateInput(pv=100, ev=100, ac=100, bac=0)


# =============================================================================
# Structured error contract
# =============================================================================


class TestStructuredErrors:
    def test_error_types_render_their_tag(self):
        assert str(ToolValidationError("bad input")) == "[ValidationError] bad input"
        assert str(ToolComputationError("maths rejected")) == "[ComputationError] maths rejected"
        assert str(ToolInternalError("oops")) == "[InternalError] oops"

    def test_wrapper_retags_value_error_as_computation_error(self):
        @structured_errors
        def boom():
            raise ValueError("bad")

        with pytest.raises(ToolComputationError, match=r"\[ComputationError\] bad"):
            boom()

    def test_wrapper_hides_unexpected_internals(self):
        @structured_errors
        def boom():
            raise RuntimeError("secret internal detail")

        with pytest.raises(ToolInternalError) as exc_info:
            boom()
        assert "secret internal detail" not in str(exc_info.value)
        assert "[InternalError]" in str(exc_info.value)

    async def test_domain_error_on_the_wire_is_tagged_and_traceback_free(self):
        """A domain error raised inside a tool surfaces to the client as a tagged
        message with no Python traceback."""
        with pytest.raises(FastMCPToolError) as exc_info:
            await mcp.call_tool(
                "estimate_task_duration",
                {"task": {"optimistic": 10, "most_likely": 5, "pessimistic": 14}},
            )
        message = str(exc_info.value)
        assert "[ComputationError]" in message
        assert "Traceback" not in message
