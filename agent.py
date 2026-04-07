from typing import Annotated
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage
from tools import search_flights, search_hotels, calculate_budget, get_current_date
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()

# 1. Đọc System Prompt
with open("system_prompt.txt", "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

# 2. Khai báo State
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 3. Khởi tạo LLM và Tools
tools_list = [search_flights, search_hotels, calculate_budget, get_current_date]
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools_list)

# 4. Agent Node
def agent_node(state: AgentState):
    messages = state["messages"]
    if not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
    
    response = llm_with_tools.invoke(messages)
    
    # === LOGGING ===
    if response.tool_calls:
        for tc in response.tool_calls:
            console.print(f"[dim yellow]⚗️ Gọi tool: {tc['name']}({tc['args']})[/dim yellow]")
        
    return {"messages": [response]}

# 5. Xây dựng Graph
builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)

tool_node = ToolNode(tools_list)
builder.add_node("tools", tool_node)

# 5. Khai báo edges
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)

# 6. Chat loop
if __name__ == "__main__":
    console.print(Panel("[bold cyan]TravelBuddy – Trợ lý Du lịch Thông minh[/bold cyan]\n[yellow]Gõ 'quit' để thoát[/yellow]", style="bold blue"))
    
    config = {"configurable": {"thread_id": "1"}}
    while True:
        try:
            user_input = console.input("\n[bold green]Bạn 👤:[/] ").strip()
        except EOFError:
            break
        if user_input.lower() in ["quit", "exit", "q"]:
            break
            
        with console.status("[bold magenta]TravelBuddy đang suy nghĩ...[/bold magenta]", spinner="dots"):
            result = graph.invoke({"messages": [("human", user_input)]}, config=config)
            
        final = result["messages"][-1]
        console.print(Panel(Markdown(final.content), title="[bold cyan]TravelBuddy 🤖[/bold cyan]", border_style="cyan"))