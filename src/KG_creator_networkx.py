import pandas as pd
import networkx as nx
import json
import os
from pathlib import Path

def load_data():
    # Get the project root directory (parent of src)
    root_dir = Path(__file__).parent.parent
    
    # Load the CSV files from the data directory
    concepts_df = pd.read_csv(root_dir / 'data' / 'concepts.csv')
    connections_df = pd.read_csv(root_dir / 'data' / 'connections.csv')
    
    return concepts_df, connections_df

def create_knowledge_graph():
    # Load data
    concepts_df, connections_df = load_data()
    
    # Create a directed graph
    G = nx.DiGraph()
    
    # Add all concepts as nodes
    for _, row in concepts_df.dropna(subset=['node_id']).iterrows():
        G.add_node(row['node_id'], 
                  type='concept',
                  name=row['node_name'],
                  complexity=row['Complexity'])
    
    # Process connections based on type
    for _, row in connections_df.iterrows():
        connection_id = row['ID']
        connection_type = row['connection_type']
        
        # Check if all required nodes exist
        nodes_exist = True
        for col in ['node_id1', 'node_id2', 'node_id3']:
            if pd.notna(row[col]) and row[col] not in G:
                print(f"Warning: Node {row[col]} referenced in connection {connection_id} doesn't exist")
                nodes_exist = False
        
        if not nodes_exist:
            continue
            
        if connection_type == 'contains':
            # For 'contains' relationships, create direct edges
            if pd.notna(row['node_id1']) and pd.notna(row['node_id2']):
                G.add_edge(row['node_id1'], row['node_id2'], 
                          relationship='contains', 
                          connection_id=connection_id)
        else:
            # For other relationships (like 'related'), reify them
            G.add_node(connection_id, 
                      type='reified_connection',
                      connection_type=connection_type)
            
            # Connect source nodes to the reified connection
            if pd.notna(row['node_id1']):
                G.add_edge(row['node_id1'], connection_id, role='neighbor')
                G.add_edge(connection_id, row['node_id1'], role='neighbor')
            
            # Connect the reified connection to target nodes
            if pd.notna(row['node_id2']):
                G.add_edge(connection_id, row['node_id2'], role='neighbor')
                G.add_edge(row['node_id2'], connection_id, role='neighbor')
                
            # Handle third node if present (for higher-order connections)
            if pd.notna(row['node_id3']):
                G.add_edge(connection_id, row['node_id3'], role='neighbor')
                G.add_edge(row['node_id3'], connection_id, role='neighbor')
    
    return G

def analyze_graph(G):
    print(f"Graph has {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Count node types
    concept_count = sum(1 for _, attr in G.nodes(data=True) if attr.get('type') == 'concept')
    reified_count = sum(1 for _, attr in G.nodes(data=True) if attr.get('type') == 'reified_connection')
    
    print(f"Concepts: {concept_count}")
    print(f"Reified connections: {reified_count}")
    
    # Count direct relationships vs reified relationships
    direct_edges = sum(1 for _, _, attr in G.edges(data=True) if 'relationship' in attr)
    reified_edges = sum(1 for _, _, attr in G.edges(data=True) if 'role' in attr)
    
    print(f"Direct 'contains' relationships: {direct_edges}")
    print(f"Edges to/from reified connections: {reified_edges}")
    
    # Find nodes with highest degree (most connections)
    top_nodes = sorted(G.degree, key=lambda x: x[1], reverse=True)[:5]
    print("Top 5 most connected nodes:")
    for node, degree in top_nodes:
        print(f"  {node}: {degree} connections")

def trace_container_path(G, node_id, path=None):
    """Recursively trace back through container relationships"""
    if path is None:
        path = [node_id]
    
    # Find nodes that contain this node
    containers = []
    for source, target, data in G.edges(data=True):
        if target == node_id and 'relationship' in data and data['relationship'] == 'contains':
            containers.append(source)
    
    if not containers:
        return path
    
    # To avoid cycles, only trace through containers we haven't seen
    for container in containers:
        if container not in path:
            new_path = path + [container]
            full_path = trace_container_path(G, container, new_path)
            if full_path:
                return full_path
    
    return path

def explore_node(G, node_id):
    """Explore a node and its connections"""
    if node_id not in G:
        print(f"Node {node_id} not found in the graph")
        return
    
    try:
        node_type = G.nodes[node_id].get('type', 'unknown')
        print(f"\nExploring {'concept' if node_type == 'concept' else 'reified connection'}: {node_id}")
        print("Attributes:", dict(G.nodes[node_id]))  # Convert to dict for safer printing
        
        # Add container traceback
        container_path = trace_container_path(G, node_id)
        if len(container_path) > 1:  # If there's more than just the current node
            print("\nContainer hierarchy:")
            path_str = " → ".join(f"{node} ({G.nodes[node].get('name', node)})" 
                                for node in container_path)
            print(f"  {path_str}")
        
        # Find containment relationships
        contains = []
        contained_by = []
        for source, target, data in G.edges(data=True):
            if 'relationship' in data and data['relationship'] == 'contains':
                if source == node_id:
                    contains.append(target)
                elif target == node_id:
                    contained_by.append(source)
        
        if contains:
            print("\nContains:")
            for target in contains:
                print(f"  - {target} ({G.nodes[target].get('name', target)})")
        if contained_by:
            print("\nContained by:")
            for source in contained_by:
                print(f"  - {source} ({G.nodes[source].get('name', source)})")
        
        # Handle exploration differently based on node type
        if node_type == 'concept':
            # Find related concepts through reified connections
            related_concepts = {}
            for neighbor in G.neighbors(node_id):
                if G.nodes[neighbor].get('type') == 'reified_connection':
                    connection_type = G.nodes[neighbor].get('connection_type', 'related')
                    # Find other concepts connected to this reified connection
                    related = [(n, neighbor) for n in G.neighbors(neighbor) 
                             if G.nodes[n].get('type') == 'concept' and n != node_id]
                    if related:
                        if connection_type not in related_concepts:
                            related_concepts[connection_type] = []
                        related_concepts[connection_type].extend(related)
            
            if related_concepts:
                print("\nRelated concepts:")
                for rel_type, concepts in related_concepts.items():
                    print(f"\n  {rel_type}:")
                    for concept, connection_id in set(concepts):  # Remove duplicates
                        print(f"    - {concept} ({G.nodes[concept].get('name', concept)}) "
                              f"through {connection_id}")
        
        elif node_type == 'reified_connection':
            # For reified connections, show all connected concepts
            connected_concepts = [n for n in G.neighbors(node_id) 
                               if G.nodes[n].get('type') == 'concept']
            if connected_concepts:
                print("\nConnects concepts:")
                for concept in connected_concepts:
                    print(f"  - {concept} ({G.nodes[concept].get('name', concept)})")
    
    except Exception as e:
        print(f"Error exploring node {node_id}: {str(e)}")


def export_to_json(G, filename="knowledge_graph.json"):
    """
    Export the knowledge graph to a simplified JSON format that's easier for LLMs to process.
    Focuses on clear representation of concepts and their relationships.
    """
    # Get the project root directory
    root_dir = Path(__file__).parent.parent
    
    # Create output directory if it doesn't exist
    output_dir = root_dir / 'output'
    output_dir.mkdir(exist_ok=True)
    
    # Prepare the full output path
    output_path = output_dir / filename
    
    # Prepare the simplified structure
    graph_data = {
        "concepts": {},
        "relationships": []
    }
    
    # Add concepts with minimal metadata
    for node, attrs in G.nodes(data=True):
        if attrs.get('type') == 'concept':
            graph_data["concepts"][node] = {
                "name": attrs.get('name', node),
                "complexity": attrs.get('complexity', "N/A"),
                "contains": [],     # List of concepts this one contains
                "contained_by": [], # List of concepts that contain this one
                "related": {}       # Dict of related concepts grouped by relationship type
            }
    
    # Process all edges to build relationships
    for source, target, attrs in G.edges(data=True):
        if 'relationship' in attrs and attrs['relationship'] == 'contains':
            # Handle direct contains relationships
            if source in graph_data["concepts"] and target in graph_data["concepts"]:
                graph_data["concepts"][source]["contains"].append(target)
                graph_data["concepts"][target]["contained_by"].append(source)
        
        elif 'role' in attrs and attrs['role'] == 'neighbor':
            # Handle reified relationships
            if source in graph_data["concepts"] and target in G.nodes:
                connection_type = G.nodes[target].get('connection_type', 'related')
                
                # Find all other concepts connected to this reified connection
                neighbors = [n for n in G.neighbors(target) 
                           if n in graph_data["concepts"] and n != source]
                
                # Add these concepts as related
                if neighbors:
                    if connection_type not in graph_data["concepts"][source]["related"]:
                        graph_data["concepts"][source]["related"][connection_type] = []
                    graph_data["concepts"][source]["related"][connection_type].extend(neighbors)
    
    # Remove duplicates from related lists
    for concept_data in graph_data["concepts"].values():
        for rel_type in concept_data["related"]:
            concept_data["related"][rel_type] = list(set(concept_data["related"][rel_type]))
    
    # Add a simple explanation for LLMs
    graph_data["explanation"] = """
    This knowledge graph shows concepts and their relationships.
    - Each concept may contain other concepts (hierarchical relationship)
    - Each concept may be related to other concepts in various ways
    
    To find relationships between concepts:
    1. Check if one concept contains the other
    2. Look for related concepts and the type of relationship
    """
    
    # Write to file
    with open(output_path, 'w') as f:
        json.dump(graph_data, f, indent=2)
    
    print(f"Knowledge graph exported to {output_path}")
    return graph_data

if __name__ == "__main__":
    # Create the knowledge graph
    knowledge_graph = create_knowledge_graph()
    
    # Analyze the graph
    analyze_graph(knowledge_graph)
    
    # Explore some important nodes
    explore_node(knowledge_graph, "LIOP")  # A concept node
    explore_node(knowledge_graph, "RLFIO")  # A reified connection
    explore_node(knowledge_graph, "b")  # A deep node
    
    # Export to JSON for LLM consumption
    export_to_json(knowledge_graph, "knowledge_graph.json")
    
    print("\nKnowledge graph successfully created and stored in 'knowledge_graph' variable") 