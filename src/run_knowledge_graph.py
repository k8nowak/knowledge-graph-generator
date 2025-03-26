## This script is used to create a knowledge graph and send it to Claude for analysis.
## Use lines 104-112 to vary what is sent to Claude.

from knowledge_graph import (
    create_knowledge_graph,
    analyze_graph,
    explore_node,
    export_to_json
)
import anthropic
from dotenv import load_dotenv
from pathlib import Path
import os
import json

def load_environment():
    # """Load environment variables from .env file"""
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(env_path)

def send_to_claude(context, prompt, knowledge_graph_data):
    
    # Initialize the Anthropic client with your API key
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
    
    
    client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key=api_key,
)
    if(context):
        print("Sending to Claude with context")
        # Convert knowledge graph data to a string format
        graph_context = json.dumps(knowledge_graph_data, indent=2)
        
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": f"""
                
                
                Here is the task at hand:   
                
                {prompt}
                
                Here is a knowledge graph in JSON format that represents concepts and their relationships.                
                {graph_context}
                
                First, find the most relevant concept or skill to the task at hand.
                Then, find that concept or skills' closest neighbors, parents, or children.
                Finally, answer the task at hand.
                Limit yourself to terminology used in the knowledge graph.
                """
            }]
    )
    else:
        print("Sending to Claude without context")
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            messages=[{"role": "user", "content": f"""
                       You are an expert in the field of math education.
                       Here is what I want you to do: {prompt}
            """}]
        )
    
    # Extract the text content from the message
    response_content = message.content[0].text
    
    # Format the response
    formatted_response = "\n" + "="*50 + "\n"
    formatted_response += "Claude's Analysis\n"
    formatted_response += "="*50 + "\n\n"
    formatted_response += response_content
    formatted_response += "\n" + "="*50
    
    return formatted_response



def main():
    # Load environment variables
    load_environment()
    
    # Create the knowledge graph
    knowledge_graph = create_knowledge_graph()
    
    # # Analyze the graph
    # analyze_graph(knowledge_graph)
    
    # # Explore some important nodes
    # explore_node(knowledge_graph, "LIOP")  # A concept node
    # explore_node(knowledge_graph, "RLFIO")  # A reified connection
    # explore_node(knowledge_graph, "b")  # A deep node
    
    # Export to JSON for LLM consumption
    graph_data = export_to_json(knowledge_graph, "knowledge_graph.json")
    
    print("\nKnowledge graph successfully created and stored in 'knowledge_graph' variable")
    
    # Here are some example prompts to send in the next part.
    prompt_WU = "I am about to plan a lesson on graphing a line given its equation, by finding solutions to the equation and plotting the solutions. Identify an important idea this depends on, and recommend a warm-up question that addresses that idea."
    prompt_PR = "An 8th grade student is unable to find the initial value of a function, given a graph of the function. What prerequisite concepts or skills might need to be remediated?"
    prompt_S = "Write me 5 short, straightforward questions that would assess whether an 8th grader understood the connections between the equation y=2x+5 and a graph of this line."
    
    # Send to Claude if API key is configured
    try:
        # Set the first argument to True if you want to send the knowledge graph as context to Claude, false if you don't.
        response = send_to_claude(False,prompt_S,graph_data)
        print("\nClaude's response:")
        print(response)
    except ValueError as e:
        print(f"\nConfiguration error: {str(e)}")
    except Exception as e:
        print(f"\nError sending to Claude: {str(e)}")
    
    return knowledge_graph

if __name__ == "__main__":
    main() 