"""
ai/agent/agent.py — the LangChain tool-calling reading-tutor agent.
LLM: LLaMA3 via Groq (fast + free tier). Tools: see tools.py.

The agent is built fresh per request with tools bound to that child's
ID, and is given the child's stored profile_summary as context so
responses reflect what's been learned about them in past sessions.
"""

from bson import ObjectId
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.config import settings
from app.database import child_profiles_collection
from app.ai.agent.tools import create_tools_for_child

SYSTEM_PROMPT = """You are LexiLoop's reading tutor, a warm and patient AI \
assistant helping a child with dyslexia practice reading and writing.

Rules:
- Keep language simple, encouraging, and age-appropriate.
- Never make the child feel bad about mistakes — reversals and reading \
struggles are normal parts of dyslexia, not failures.
- Use the simplify_text tool if the child seems confused by wording.
- Use retrieve_story when the child wants to read something or practice.
- Use log_mood whenever the child expresses a feeling about the session.
- Use update_child_profile at the end of a meaningful exchange to record \
anything worth remembering next time (interests, specific struggles, \
what encouragement worked).

What we know about this child so far:
{child_context}
"""


async def _get_child_context(child_id: str) -> str:
    child = await child_profiles_collection().find_one({"_id": ObjectId(child_id)})
    if not child:
        return "No prior information yet — this is a new profile."
    summary = child.get("profile_summary") or "No summary recorded yet."
    reversals = child.get("common_reversals", [])
    level = child.get("reading_level", "unknown")
    return (
        f"Name: {child.get('name')}, age {child.get('age')}, "
        f"reading level: {level}.\n"
        f"Recent letter reversals seen: {reversals[-10:] if reversals else 'none yet'}.\n"
        f"Summary: {summary}"
    )


async def run_agent(child_id: str, message: str) -> tuple[str, list[str]]:
    llm = ChatGroq(
        model=settings.GROQ_MODEL,
        api_key=settings.GROQ_API_KEY,
        temperature=0.4,
    )
    tools = create_tools_for_child(child_id)
    child_context = await _get_child_context(child_id)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT.format(child_context=child_context)),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=False)

    result = await executor.ainvoke({"input": message})

    tool_calls_used = [
        step[0].tool for step in result.get("intermediate_steps", [])
    ]
    return result["output"], tool_calls_used
