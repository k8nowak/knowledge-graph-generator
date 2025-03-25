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
    skills_df = pd.read_csv(root_dir / 'data' / 'skills.csv')  # Add skills data
    
    return concepts_df, connections_df, skills_df

def add_node_to_graph(G, node_id, node_type, name, **attributes):
    """Helper function to add nodes with consistent attributes"""
    G.add_node(node_id, type=node_type, name=name, **attributes)

def get_node_name(G, node_id):
    """Helper function to get node name with fallback"""
    return G.nodes[node_id].get('name', node_id)

def create_knowledge_graph():
    # Load data
    concepts_df, connections_df, skills_df = load_data()
    
    G = nx.DiGraph()
    
    # Create node_skills using dictionary
    node_skills = {}
    for _, row in skills_df.dropna(subset=['node_id']).iterrows():
        node_id = row['node_id']
        if node_id not in node_skills:
            node_skills[node_id] = []
        node_skills[node_id].append({
            'skill_id': row['skill_id'],
            'description': row['skill_description']
        })
    
    # Add concepts as nodes
    for _, row in concepts_df.dropna(subset=['node_id']).iterrows():
        add_node_to_graph(G, 
                         row['node_id'],
                         'concept',
                         row['node_name'],
                         complexity=row['Complexity'],
                         skills=node_skills.get(row['node_id'], []))

    def process_connection(row):
        """Helper function to process a single connection"""
        connection_id = row['ID']
        connection_type = row['connection_type']
        
        # Check if all referenced nodes exist
        nodes = [row[f'node_id{i}'] for i in range(1, 4) if pd.notna(row[f'node_id{i}'])]
        if not all(node in G for node in nodes):
            print(f"Warning: Some nodes referenced in connection {connection_id} don't exist")
            return
        
        if connection_type == 'contains':
            if pd.notna(row['node_id1']) and pd.notna(row['node_id2']):
                G.add_edge(row['node_id1'], row['node_id2'], 
                          relationship='contains', 
                          connection_id=connection_id)
        else:
            # Add reified connection node
            node_name = concepts_df[concepts_df['node_id'] == connection_id]['node_name'].iloc[0]
            add_node_to_graph(G, connection_id, 'reified_connection', node_name, connection_type=connection_type)
            
            # Add bidirectional edges for all connected nodes
            for node in nodes:
                G.add_edge(node, connection_id, role='neighbor')
                G.add_edge(connection_id, node, role='neighbor')
    
    # Process all connections
    connections_df.apply(process_connection, axis=1)
    
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
    containers = [source for source, target, data in G.edges(data=True)
                 if target == node_id and data.get('relationship') == 'contains']
    
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

def explore_concept_relationships(G, node_id):
    """Helper function to explore concept relationships"""
    related_concepts = {}
    for neighbor in G.neighbors(node_id):
        if G.nodes[neighbor].get('type') == 'reified_connection':
            connection_type = G.nodes[neighbor].get('connection_type', 'related')
            related = [(n, neighbor) for n in G.neighbors(neighbor) 
                      if G.nodes[n].get('type') == 'concept' and n != node_id]
            if related:
                related_concepts.setdefault(connection_type, []).extend(related)
    
    if related_concepts:
        print("\nRelated concepts:")
        for rel_type, concepts in related_concepts.items():
            print(f"\n  {rel_type}:")
            for concept, connection_id in set(concepts):
                print(f"    - {concept} ({get_node_name(G, concept)}) "
                      f"through {connection_id} ")

def explore_reified_connection(G, node_id):
    """Helper function to explore reified connection"""
    connected_concepts = [n for n in G.neighbors(node_id) 
                         if G.nodes[n].get('type') == 'concept']
    if connected_concepts:
        print("\nConnects concepts:")
        for concept in connected_concepts:
            print(f"  - {concept} ({get_node_name(G, concept)})")

def explore_node(G, node_id):
    """Explore a node and its connections"""
    if node_id not in G:
        print(f"Node {node_id} not found in the graph")
        return
    
    try:
        node_attrs = G.nodes[node_id]
        node_type = node_attrs.get('type', 'unknown')
        print(f"\nExploring {node_type}: {node_id} ({get_node_name(G, node_id)})")
        
        # Print attributes (excluding skills)
        print("\nAttributes:")
        attrs = {k: v for k, v in node_attrs.items() if k != 'skills'}
        for key, value in attrs.items():
            print(f"  {key}: {value}")
        
        # Print skills if they exist
        if skills := node_attrs.get('skills', []):
            print("\nSkills:")
            for skill in skills:
                print(f"  - {skill['skill_id']}: {skill['description']}")
        
        # Print container hierarchy
        if container_path := trace_container_path(G, node_id):
            if len(container_path) > 1:
                print("\nContainer hierarchy:")
                path_str = " → ".join(f"{node} ({get_node_name(G, node)})" for node in container_path)
                print(f"  {path_str}")
        
        # Get containment relationships
        contains = [target for source, target, data in G.edges(data=True)
                   if source == node_id and data.get('relationship') == 'contains']
        contained_by = [source for source, target, data in G.edges(data=True)
                       if target == node_id and data.get('relationship') == 'contains']
        
        if contains:
            print("\nContains:")
            for target in contains:
                print(f"  - {target} ({get_node_name(G, target)})")
        if contained_by:
            print("\nContained by:")
            for source in contained_by:
                print(f"  - {source} ({get_node_name(G, source)})")
        
        # Handle concept/reified connection specific exploration
        if node_type == 'concept':
            explore_concept_relationships(G, node_id)
        elif node_type == 'reified_connection':
            explore_reified_connection(G, node_id)
    
    except Exception as e:
        print(f"Error exploring node {node_id}: {str(e)}")

def export_to_json(G, filename="knowledge_graph.json"):
    """
    Export the knowledge graph to a simplified JSON format that's easier for LLMs to process.
    """
    # Get the project root directory
    root_dir = Path(__file__).parent.parent
    output_dir = root_dir / 'output'
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / filename
    
    # Prepare the simplified structure
    graph_data = {
        "concepts": {},
        "relationships": []
    }
    
    # Add concepts with metadata including skills
    for node, attrs in G.nodes(data=True):
        if attrs.get('type') == 'concept':
            graph_data["concepts"][node] = {
                "name": attrs.get('name', node),
                "complexity": attrs.get('complexity', "N/A"),
                "skills": attrs.get('skills', []),
                "contains": [],     
                "contained_by": [], 
                "related": {}       
            }
    
    # Process all edges to build relationships
    for source, target, attrs in G.edges(data=True):
        if 'relationship' in attrs and attrs['relationship'] == 'contains':
            if source in graph_data["concepts"] and target in graph_data["concepts"]:
                graph_data["concepts"][source]["contains"].append(target)
                graph_data["concepts"][target]["contained_by"].append(source)
        
        elif 'role' in attrs and attrs['role'] == 'neighbor':
            if source in graph_data["concepts"] and target in G.nodes:
                connection_type = G.nodes[target].get('connection_type', 'related')
                neighbors = [n for n in G.neighbors(target) 
                           if n in graph_data["concepts"] and n != source]
                
                if neighbors:
                    if connection_type not in graph_data["concepts"][source]["related"]:
                        graph_data["concepts"][source]["related"][connection_type] = []
                    graph_data["concepts"][source]["related"][connection_type].extend(neighbors)
    
    # Remove duplicates from related lists
    for concept_data in graph_data["concepts"].values():
        for rel_type in concept_data["related"]:
            concept_data["related"][rel_type] = list(set(concept_data["related"][rel_type]))
    
    # Add explanation for LLMs
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