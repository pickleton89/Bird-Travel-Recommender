#!/usr/bin/env python3
"""
Comprehensive MCP Tools Integration Tests

Tests all 30 MCP tools across 6 categories with the current modular architecture.
"""

import pytest
import asyncio
from unittest.mock import patch

# Import the current MCP server
from src.bird_travel_recommender.mcp.server import BirdTravelMCPServer


@pytest.mark.asyncio
class TestMCPToolsComprehensive:
    """Comprehensive test suite for all 30 MCP tools."""

    @pytest.fixture
    def mcp_server(self):
        """Create MCP server instance for testing."""
        with patch.dict(
            "os.environ",
            {"EBIRD_API_KEY": "test_key_12345", "OPENAI_API_KEY": "test_openai_key"},
        ):
            server = BirdTravelMCPServer()
            return server

    async def test_all_tools_registered(self, mcp_server):
        """Test that all 30 tools are properly registered."""
        # Use the server's list_tools method directly
        tools = mcp_server.tools

        tool_names = [tool.name for tool in tools]

        # Expected tools by category (based on server.py documentation)
        expected_species = ["validate_species", "get_regional_species_list"]
        expected_location = [
            "get_region_details",
            "get_hotspot_details",
            "find_nearest_species",
            "get_nearby_notable_observations",
            "get_nearby_species_observations",
            "get_top_locations",
            "get_regional_statistics",
            "get_location_species_list",
            "get_subregions",
            "get_adjacent_regions",
            "get_elevation_data",
        ]
        expected_pipeline = [
            "fetch_sightings",
            "filter_constraints",
            "cluster_hotspots",
            "score_locations",
            "optimize_route",
            "get_historic_observations",
            "get_seasonal_trends",
            "get_yearly_comparisons",
            "get_migration_data",
            "get_peak_times",
            "get_seasonal_hotspots",
        ]
        expected_planning = ["generate_itinerary", "plan_complete_trip"]
        expected_advisory = ["get_birding_advice"]
        expected_community = [
            "get_recent_checklists",
            "get_checklist_details",
            "get_user_stats",
        ]

        all_expected = (
            expected_species
            + expected_location
            + expected_pipeline
            + expected_planning
            + expected_advisory
            + expected_community
        )

        # Verify total count matches server expectation
        assert len(tools) == 30, f"Expected 30 tools, got {len(tools)}"

        # Verify all expected tools are present
        for tool_name in all_expected:
            assert tool_name in tool_names, (
                f"Tool '{tool_name}' not found in registered tools"
            )

        # Verify category counts match server documentation
        assert len(expected_species) == 2
        assert len(expected_location) == 11
        assert len(expected_pipeline) == 11
        assert len(expected_planning) == 2
        assert len(expected_advisory) == 1
        assert len(expected_community) == 3

    async def test_tool_schemas_valid(self, mcp_server):
        """Test that all tools have properly defined schemas."""
        tools = mcp_server.tools

        # Verify every tool has required schema elements
        for tool in tools:
            assert hasattr(tool, "name"), f"Tool missing name: {tool}"
            assert hasattr(tool, "description"), f"Tool {tool.name} missing description"
            assert hasattr(tool, "inputSchema"), f"Tool {tool.name} missing inputSchema"

            schema = tool.inputSchema
            assert isinstance(schema, dict), f"Tool {tool.name} schema not a dict"
            assert "type" in schema, f"Tool {tool.name} schema missing type"
            assert "properties" in schema, f"Tool {tool.name} schema missing properties"

    @patch(
        "src.bird_travel_recommender.mcp.handlers.species.SpeciesHandlers.handle_validate_species"
    )
    async def test_species_tool_execution(self, mock_validate, mcp_server):
        """Test execution of species category tools."""
        mock_validate.return_value = {
            "success": True,
            "validated_species": [
                {"species_code": "norcar", "common_name": "Northern Cardinal"}
            ],
        }

        # Test tool execution through the router
        result = await mcp_server._route_tool_call(
            "validate_species", {"species_names": ["Northern Cardinal"]}
        )

        assert result["success"] is True
        assert "validated_species" in result
        mock_validate.assert_called_once()

    async def test_unknown_tool_error(self, mcp_server):
        """Test error handling for unknown tools."""
        try:
            await mcp_server._route_tool_call("unknown_tool", {"param": "value"})
            assert False, "Should have raised an exception"
        except ValueError as e:
            assert "Unknown tool: unknown_tool" in str(e)

    @patch(
        "src.bird_travel_recommender.mcp.handlers.species.SpeciesHandlers.handle_validate_species"
    )
    async def test_tool_execution_error_handling(self, mock_validate, mcp_server):
        """Test error handling during tool execution."""
        mock_validate.side_effect = ValueError("Test error message")

        try:
            await mcp_server._route_tool_call(
                "validate_species", {"species_names": ["Test Species"]}
            )
            assert False, "Should have raised an exception"
        except ValueError as e:
            assert "Test error message" in str(e)

    async def test_concurrent_tool_execution(self, mcp_server):
        """Test that multiple tools can be executed concurrently."""
        with (
            patch(
                "src.bird_travel_recommender.mcp.handlers.species.SpeciesHandlers.handle_validate_species"
            ) as mock_species,
            patch(
                "src.bird_travel_recommender.mcp.handlers.location.LocationHandlers.handle_get_region_details"
            ) as mock_region,
        ):
            mock_species.return_value = {"success": True, "validated_species": []}
            mock_region.return_value = {"success": True, "region_info": {}}

            tasks = [
                mcp_server._route_tool_call(
                    "validate_species", {"species_names": ["Cardinal"]}
                ),
                mcp_server._route_tool_call("get_region_details", {"region": "US-MA"}),
            ]

            results = await asyncio.gather(*tasks)

            assert len(results) == 2
            for result in results:
                assert result["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
