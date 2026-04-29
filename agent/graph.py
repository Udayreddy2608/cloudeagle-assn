import logging
from typing import Any
import json

from openai import OpenAI
from langgraph.graph import StateGraph, START, END
import httpx

from agent.state import AgentState, CountryIntent
from agent.prompts import INTENT_SYSTEM_PROMPT, SYNTHESIS_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

COUNTRY_API_URL = "https://restcountries.com/v3.1/name/{country}"
COUNTRY_API_FIELDS = "name,capital,population,currencies,languages,area,region,subregion,flags"

class CountryAgent:
    def __init__(self):
        self.client = OpenAI()
        self.graph = self._build_graph()
    
    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("intent",    self._intent_node)
        graph.add_node("fetch",     self._fetch_node)
        graph.add_node("synthesize", self._synthesis_node)

        graph.add_edge(START, "intent")

        graph.add_conditional_edges(
            "intent",
            self._should_fetch,
            {"fetch": "fetch", "synthesize": "synthesize"}
        )

        graph.add_edge("fetch", "synthesize")

        graph.add_edge("synthesize", END)

        return graph.compile()
    
    def _intent_node(self, state: AgentState) -> dict[str, Any]:
        logger.info("intent_node | query=%r", state["query"])
        try:
            response = self.client.responses.parse(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                    {"role": "system", "content": state["query"]}
                ],
                text_format=CountryIntent,
            )
            intent: CountryIntent = response.output_parsed
            logger.info("intent_node | country=%r fields=%s", intent.country, intent.fields)

            if not intent.country:
                return {
                    "intent": None,
                    "error": "Could not identify a country in your question. Please try again.",
                }

            return {"intent": intent, "error": None}


        except Exception as exc:
            logger.error("intent_node | failed: %s", exc)
            return {
                "intent": None,
                "error": "Something went wrong while parsing your question.",
            }
        
    def _fetch_node(self, state: AgentState) -> dict[str, Any]:
        country = state["intent"].country
        logger.info("fetch_node | country=%r", country)

        url = COUNTRY_API_URL.format(country=country)
        try:
            with httpx.Client(timeout= 8.0) as http:
                resp = http.get(url, params= {"fields": COUNTRY_API_FIELDS})
                if resp.status_code == 404:
                    logger.warning("fetch_node | not found: %r", country)
                    return {
                        "raw_data": None,
                        "error": f"No country found matching '{country}'. Check the spelling and try again."
                    }
                
                resp.raise_for_status()
                results = resp.json()
                best = self._best_match(results, country)
                logger.info("fetch_node | matched=%r", best.get("name", {}).get("common"))
                return {"raw_data": best, "error": None}
            
        except httpx.TimeoutException: 
            logger.error("fetch_node | timeout for %r", country)
            return {"raw_data": None, "error": "Request timed out. Please try again."}
        except Exception as exc:

            logger.error("fetch_node | unexpected error: %s", exc)
            return {"raw_data": None, "error": "Failed to fetch country data."}
        
    def _synthesis_node(self, state: AgentState) -> dict[str, Any]:
        logger.info("synthesis_node | starting")

        if state.get("error"):
            logger.info("synthesis_node | error path: %r", state["error"])
            return {"answer": state["error"]}

        raw_data = state.get("raw_data")
        if not raw_data:
            return {"answer": "No data available for that country."}

        intent: CountryIntent = state["intent"]
        filtered = self._filter_fields(raw_data, intent.fields)
        logger.info("synthesis_node | fields=%s", intent.fields)

        try:
            response = self.client.responses.create(
                model="gpt-4o-mini",
                input=[
                    {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {state['query']}\n\n"
                            f"Country data:\n{json.dumps(filtered, ensure_ascii=False)}"
                        ),
                    },
                ],
            )

            answer = response.output[0].content[0].text.strip()
            logger.info("synthesis_node | answer=%r", answer)
            return {"answer": answer}

        except Exception as exc:
            logger.error("synthesis_node | failed: %s", exc)
            return {"answer": "Sorry, I could not generate an answer. Please try again."}

    def _filter_fields(self, raw_data: dict, fields: list[str]) -> dict:
        """
        Only pass the fields the user asked about to the LLM.
        Always include name so the LLM knows which country it's answering about.
        """
        field_map = {
            "population": "population",
            "capital":    "capital",
            "currencies": "currencies",
            "languages":  "languages",
            "area":       "area",
            "region":     "region",
            "subregion":  "subregion",
            "flag":       "flags",
        }

        filtered = {"name": raw_data.get("name")} 

        for field in fields:
            api_key = field_map.get(field)
            if api_key and api_key in raw_data:
                filtered[api_key] = raw_data[api_key]

        return filtered
    
    def _should_fetch(self, state: AgentState) -> str:
        if state.get("intent") and not state.get("error"):
            return "fetch"
        return "synthesize"
    
    def _best_match(self, results: list[dict], query: str) -> dict:
        q = query.lower()
        for r in results:
            common   = r.get("name", {}).get("common",   "").lower()
            official = r.get("name", {}).get("official", "").lower()
            if q == common or q == official:
                return r
        return results[0]
        
    def run(self, query: str) -> dict[str, Any]:
        if not query or not query.strip():
            return {"answer": "Please enter a question about a country.", "error": "empty_query"}

        result = self.graph.invoke({"query": query.strip()})
        
  
        return {
            "answer": result.get("answer"),
            "intent": result.get("intent"),
            "error":  result.get("error"),
        }
    
