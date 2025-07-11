from pocketflow import Node
from .utils.call_llm import call_llm
import logging

logger = logging.getLogger(__name__)


class GetQuestionNode(Node):
    def exec(self, _):
        # Get question directly from user input
        user_question = input("Enter your question: ")
        return user_question

    def post(self, shared, prep_res, exec_res):
        # Store the user's question
        shared["question"] = exec_res
        return "default"  # Go to the next node


class AnswerNode(Node):
    def prep(self, shared):
        # Read question from shared
        return shared["question"]

    def exec(self, question):
        # Call LLM to get the answer
        return call_llm(question)

    def post(self, shared, prep_res, exec_res):
        # Store the answer in shared
        shared["answer"] = exec_res


# MIGRATED: ValidateSpeciesNode has been moved to nodes/validation/species.py
# Original class definition removed to avoid import conflicts


# MIGRATED: FetchSightingsNode and AsyncFetchSightingsNode have been moved to:
# - nodes/fetching/sightings.py
# - nodes/fetching/async_sightings.py
# Original class definitions removed to avoid import conflicts

# END OF MIGRATED FetchSightingsNode and AsyncFetchSightingsNode


# MIGRATED: FilterConstraintsNode has been moved to nodes/processing/constraints.py
# Original class definition removed to avoid import conflicts


# MIGRATED: ClusterHotspotsNode has been moved to nodes/processing/clustering.py
# Original class definition removed to avoid import conflicts


# MIGRATED: ScoreLocationsNode has been moved to nodes/processing/scoring.py
# Original class definition removed to avoid import conflicts


# MIGRATED: OptimizeRouteNode has been moved to nodes/processing/routing.py
# Original class definition removed to avoid import conflicts


# MIGRATED: GenerateItineraryNode has been moved to nodes/processing/itinerary.py
# Original class definition removed to avoid import conflicts
