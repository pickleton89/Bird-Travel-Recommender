#!/usr/bin/env python3
"""
MCP vs PocketFlow Parity Testing

This script tests the functional parity between the MCP server implementation
and the original PocketFlow pipeline implementation to ensure both architectures
produce equivalent results for birding requests.
"""

import asyncio
import json
import logging
import sys
import time
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass
import pytest

# Skip entire module if agent_flow is not available
pytest.skip("agent_flow module not yet implemented", allow_module_level=True)

# from bird_travel_recommender.agent_flow import execute_agent_request
# from bird_travel_recommender.flow import run_birding_pipeline, create_test_input

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ParityTestCase:
    """Test case for comparing MCP vs PocketFlow implementations"""
    name: str
    user_request: str
    context: Dict[str, Any]
    comparison_fields: List[str]  # Fields to compare between implementations
    tolerance: Dict[str, float] = None  # Tolerance for numeric comparisons


@dataclass 
class ParityResult:
    """Result of a parity test comparison"""
    test_name: str
    mcp_success: bool
    pocketflow_success: bool
    execution_time_mcp: float
    execution_time_pocketflow: float
    data_parity: Dict[str, bool]
    overall_parity: bool
    differences: List[str]


class MCPPocketFlowParityTester:
    """Tests functional parity between MCP and PocketFlow implementations"""
    
    def __init__(self):
        self.test_cases = self._create_test_cases()
    
    def _create_test_cases(self) -> List[ParityTestCase]:
        """Create comprehensive test cases for parity testing"""
        return [
            ParityTestCase(
                name="Species Validation",
                user_request="validate bird species: Northern Cardinal, Blue Jay",
                context={"species": ["Northern Cardinal", "Blue Jay"]},
                comparison_fields=["species_count", "validation_success", "species_names"]
            ),
            
            ParityTestCase(
                name="Simple Trip Planning",
                user_request="Plan a birding trip to see Northern Cardinals in Massachusetts",
                context={
                    "species": ["Northern Cardinal"],
                    "region": "US-MA",
                    "start_location": {"lat": 42.3601, "lng": -71.0589},
                    "max_distance_km": 50,
                    "days_back": 7
                },
                comparison_fields=["trip_planning", "location_count", "route_optimization"]
            ),
            
            ParityTestCase(
                name="Multi-Species Planning",
                user_request="Plan a trip to see Cardinals and Blue Jays in Texas",
                context={
                    "species": ["Northern Cardinal", "Blue Jay"],
                    "region": "US-TX",
                    "start_location": {"lat": 32.7767, "lng": -96.7970},
                    "max_distance_km": 100,
                    "days_back": 14
                },
                comparison_fields=["species_diversity", "location_clustering", "route_length"]
            ),
            
            ParityTestCase(
                name="Location Clustering",
                user_request="Find birding hotspots for Cardinals near Boston",
                context={
                    "species": ["Northern Cardinal"],
                    "region": "US-MA",
                    "center_location": {"lat": 42.3601, "lng": -71.0589},
                    "radius_km": 25
                },
                comparison_fields=["hotspot_count", "geographic_distribution", "clustering_quality"]
            ),
            
            ParityTestCase(
                name="Route Optimization",
                user_request="Optimize a birding route for Cardinals in California",
                context={
                    "species": ["Northern Cardinal"],
                    "region": "US-CA",
                    "start_location": {"lat": 34.0522, "lng": -118.2437},
                    "max_locations": 5
                },
                comparison_fields=["route_efficiency", "total_distance", "location_ordering"]
            )
        ]
    
    async def run_parity_tests(self) -> List[ParityResult]:
        """Run all parity tests and return results"""
        print("🔬 Starting MCP vs PocketFlow Parity Tests...")
        print("=" * 70)
        
        results = []
        
        for i, test_case in enumerate(self.test_cases, 1):
            print(f"\\n🧪 Test {i}: {test_case.name}")
            print("-" * 50)
            
            # Run MCP implementation
            print("Running MCP implementation...")
            mcp_result, mcp_time = await self._run_mcp_test(test_case)
            
            # Run PocketFlow implementation  
            print("Running PocketFlow implementation...")
            pocketflow_result, pocketflow_time = await self._run_pocketflow_test(test_case)
            
            # Compare results
            parity_result = self._compare_results(
                test_case, mcp_result, pocketflow_result, mcp_time, pocketflow_time
            )
            
            results.append(parity_result)
            
            # Print test summary
            self._print_test_summary(parity_result)
        
        # Print overall summary
        self._print_overall_summary(results)
        
        return results
    
    async def _run_mcp_test(self, test_case: ParityTestCase) -> Tuple[Dict[str, Any], float]:
        """Run test case using MCP implementation"""
        start_time = time.time()
        
        try:
            response = await execute_agent_request(test_case.user_request, test_case.context)
            execution_time = time.time() - start_time
            
            # Extract relevant data for comparison
            extracted_data = self._extract_mcp_data(response, test_case)
            
            return {
                "success": True,
                "response": response,
                "extracted_data": extracted_data,
                "execution_time": execution_time
            }, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"MCP test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }, execution_time
    
    async def _run_pocketflow_test(self, test_case: ParityTestCase) -> Tuple[Dict[str, Any], float]:
        """Run test case using PocketFlow implementation"""
        start_time = time.time()
        
        try:
            # Prepare input data in the format expected by PocketFlow
            input_data = {
                "input": {
                    "species_list": test_case.context.get("species", ["Northern Cardinal"]),
                    "constraints": {
                        "start_location": test_case.context.get("start_location", {"lat": 42.3601, "lng": -71.0589}),
                        "region": test_case.context.get("region", "US-MA"),
                        "max_days": test_case.context.get("trip_duration_days", 1),
                        "max_daily_distance_km": test_case.context.get("max_distance_km", 100),
                        "days_back": test_case.context.get("days_back", 14),
                        "max_locations_per_day": 8,
                        "min_location_score": 0.3
                    }
                }
            }
            
            # Execute PocketFlow pipeline
            result = run_birding_pipeline(input_data=input_data, debug=False)
            execution_time = time.time() - start_time
            
            # Extract relevant data for comparison
            extracted_data = self._extract_pocketflow_data(result, test_case)
            
            return {
                "success": result.get("success", False),
                "pipeline_result": result,
                "extracted_data": extracted_data,
                "execution_time": execution_time
            }, execution_time
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"PocketFlow test failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_time": execution_time
            }, execution_time
    
    def _extract_mcp_data(self, response: Dict[str, Any], test_case: ParityTestCase) -> Dict[str, Any]:
        """Extract comparable data from MCP response"""
        extracted = {}
        
        response_type = response.get("type", "unknown")
        
        if response_type == "complete_trip_plan":
            trip_plan = response.get("trip_plan", {})
            
            extracted.update({
                "species_count": len(trip_plan.get("species", [])),
                "location_count": len(trip_plan.get("locations", [])),
                "route_length": trip_plan.get("route", {}).get("total_distance_km", 0),
                "trip_planning": True,
                "route_optimization": bool(trip_plan.get("route")),
                "location_clustering": bool(trip_plan.get("clusters"))
            })
        
        elif response_type == "birding_advice":
            advice = response.get("advice", "")
            extracted.update({
                "advice_length": len(advice),
                "has_recommendations": "recommend" in advice.lower(),
                "advice_type": response.get("advice_type", "general")
            })
        
        # Common fields
        extracted.update({
            "response_type": response_type,
            "success": True,
            "has_content": bool(response.get("message") or response.get("advice") or response.get("trip_plan"))
        })
        
        return extracted
    
    def _extract_pocketflow_data(self, pipeline_result: Dict[str, Any], test_case: ParityTestCase) -> Dict[str, Any]:
        """Extract comparable data from PocketFlow pipeline result"""
        extracted = {}
        
        # Basic success information
        extracted["success"] = pipeline_result.get("success", False)
        extracted["pipeline_complete"] = pipeline_result.get("success", False)
        
        # Species data
        validated_species = pipeline_result.get("validated_species", [])
        extracted["species_count"] = len(validated_species)
        extracted["validation_success"] = bool(validated_species)
        
        # Location data
        clusters = pipeline_result.get("hotspot_clusters", [])
        scored_locations = pipeline_result.get("scored_locations", [])
        extracted["hotspot_count"] = len(clusters)
        extracted["location_count"] = len(scored_locations)
        extracted["location_clustering"] = bool(clusters)
        
        # Route data
        optimized_route = pipeline_result.get("optimized_route", {})
        extracted["route_optimization"] = bool(optimized_route)
        if isinstance(optimized_route, dict):
            extracted["route_length"] = optimized_route.get("total_distance_km", 0)
        else:
            extracted["route_length"] = 0
        
        # Itinerary data
        itinerary_markdown = pipeline_result.get("itinerary_markdown", "")
        extracted["trip_planning"] = bool(itinerary_markdown)
        extracted["itinerary_length"] = len(itinerary_markdown)
        
        # Statistics from pipeline
        stats = pipeline_result.get("pipeline_statistics", {})
        fetch_stats = stats.get("fetch_stats", {})
        clustering_stats = stats.get("clustering_stats", {})
        route_stats = stats.get("route_optimization_stats", {})
        
        extracted["sightings_count"] = fetch_stats.get("total_observations", 0)
        extracted["clusters_created"] = clustering_stats.get("clusters_created", 0)
        extracted["route_distance"] = route_stats.get("total_route_distance_km", 0)
        
        return extracted
    
    def _compare_results(self, test_case: ParityTestCase, mcp_result: Dict[str, Any], 
                        pocketflow_result: Dict[str, Any], mcp_time: float, 
                        pocketflow_time: float) -> ParityResult:
        """Compare MCP and PocketFlow results for parity"""
        
        mcp_success = mcp_result.get("success", False)
        pocketflow_success = pocketflow_result.get("success", False)
        
        mcp_data = mcp_result.get("extracted_data", {})
        pocketflow_data = pocketflow_result.get("extracted_data", {})
        
        # Compare specified fields
        data_parity = {}
        differences = []
        
        for field in test_case.comparison_fields:
            mcp_value = mcp_data.get(field)
            pocketflow_value = pocketflow_data.get(field)
            
            # Handle different comparison types
            if isinstance(mcp_value, (int, float)) and isinstance(pocketflow_value, (int, float)):
                # Numeric comparison with tolerance
                tolerance = test_case.tolerance.get(field, 0.1) if test_case.tolerance else 0.1
                parity = abs(mcp_value - pocketflow_value) <= tolerance
                if not parity:
                    differences.append(f"{field}: MCP={mcp_value}, PocketFlow={pocketflow_value}")
            
            elif isinstance(mcp_value, bool) and isinstance(pocketflow_value, bool):
                # Boolean comparison
                parity = mcp_value == pocketflow_value
                if not parity:
                    differences.append(f"{field}: MCP={mcp_value}, PocketFlow={pocketflow_value}")
            
            elif isinstance(mcp_value, str) and isinstance(pocketflow_value, str):
                # String comparison (case-insensitive)
                parity = mcp_value.lower() == pocketflow_value.lower()
                if not parity:
                    differences.append(f"{field}: MCP='{mcp_value}', PocketFlow='{pocketflow_value}'")
            
            else:
                # General equality
                parity = mcp_value == pocketflow_value
                if not parity:
                    differences.append(f"{field}: MCP={mcp_value}, PocketFlow={pocketflow_value}")
            
            data_parity[field] = parity
        
        # Overall parity assessment
        overall_parity = (mcp_success and pocketflow_success and 
                         all(data_parity.values()) and len(differences) == 0)
        
        return ParityResult(
            test_name=test_case.name,
            mcp_success=mcp_success,
            pocketflow_success=pocketflow_success,
            execution_time_mcp=mcp_time,
            execution_time_pocketflow=pocketflow_time,
            data_parity=data_parity,
            overall_parity=overall_parity,
            differences=differences
        )
    
    def _print_test_summary(self, result: ParityResult) -> None:
        """Print summary for individual test"""
        status = "✅ PASS" if result.overall_parity else "❌ FAIL"
        print(f"{status} {result.test_name}")
        
        print(f"  MCP Success: {'✅' if result.mcp_success else '❌'}")
        print(f"  PocketFlow Success: {'✅' if result.pocketflow_success else '❌'}")
        print(f"  Execution Time - MCP: {result.execution_time_mcp:.2f}s, PocketFlow: {result.execution_time_pocketflow:.2f}s")
        
        if result.data_parity:
            parity_summary = [f"{k}: {'✅' if v else '❌'}" for k, v in result.data_parity.items()]
            print(f"  Data Parity: {', '.join(parity_summary)}")
        
        if result.differences:
            print(f"  Differences: {len(result.differences)}")
            for diff in result.differences[:3]:  # Show first 3 differences
                print(f"    - {diff}")
            if len(result.differences) > 3:
                print(f"    ... and {len(result.differences) - 3} more")
    
    def _print_overall_summary(self, results: List[ParityResult]) -> None:
        """Print overall parity test summary"""
        print("\\n" + "=" * 70)
        print("📊 PARITY TEST RESULTS SUMMARY")
        print("=" * 70)
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.overall_parity)
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Parity Rate: {passed_tests/total_tests*100:.1f}%")
        
        # Performance comparison
        avg_mcp_time = sum(r.execution_time_mcp for r in results) / total_tests
        avg_pocketflow_time = sum(r.execution_time_pocketflow for r in results) / total_tests
        
        print(f"\\nPerformance Comparison:")
        print(f"  Average MCP Time: {avg_mcp_time:.2f}s")
        print(f"  Average PocketFlow Time: {avg_pocketflow_time:.2f}s")
        print(f"  MCP vs PocketFlow: {avg_mcp_time/avg_pocketflow_time:.2f}x")
        
        # Success rates
        mcp_success_rate = sum(1 for r in results if r.mcp_success) / total_tests * 100
        pocketflow_success_rate = sum(1 for r in results if r.pocketflow_success) / total_tests * 100
        
        print(f"\\nSuccess Rates:")
        print(f"  MCP Success Rate: {mcp_success_rate:.1f}%")
        print(f"  PocketFlow Success Rate: {pocketflow_success_rate:.1f}%")
        
        # Failed tests details
        failed_tests = [r for r in results if not r.overall_parity]
        if failed_tests:
            print(f"\\nFailed Tests:")
            for result in failed_tests:
                print(f"  ❌ {result.test_name}")
                if result.differences:
                    print(f"    Key differences: {result.differences[0]}")


async def main():
    """Main parity testing function"""
    tester = MCPPocketFlowParityTester()
    
    try:
        results = await tester.run_parity_tests()
        
        # Determine exit code based on results
        success_rate = sum(1 for r in results if r.overall_parity) / len(results)
        
        if success_rate >= 0.8:  # 80% parity threshold
            print("\\n🎉 Parity tests PASSED! MCP and PocketFlow implementations are functionally equivalent.")
            sys.exit(0)
        else:
            print(f"\\n⚠️ Parity tests FAILED! Only {success_rate*100:.1f}% parity achieved.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Parity testing failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())