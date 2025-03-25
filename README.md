# Knowledge Graph Creator

A Python tool for creating and analyzing knowledge graphs using NetworkX.

## Features

- Create knowledge graphs from CSV data
- Support for both direct and reified relationships
- Analyze graph properties and connections
- Explore nodes and their relationships
- Export graphs to JSON format

## Installation

1. Clone this repository:
```bash
git clone https://github.com/k8nowak/knowledge-graph-generator.git
cd knowledge-graph
```

2. Create a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Prepare your data:
   - Place your `concepts.csv` and `connections.csv` files in the `data/` directory
   - Format requirements:
     - concepts.csv: node_id, node_name, Complexity
     - connections.csv: ID, connection_type, node_id1, node_id2, node_id3

2. Run the script:
```bash
python src/KG_creator_networkx.py
```

## Data Format

### concepts.csv
```csv
node_id,node_name,Complexity
NODE1,First Node,1
NODE2,Second Node,2
```

### connections.csv
```csv
ID,connection_type,node_id1,node_id2,node_id3
CONN1,contains,NODE1,NODE2,
CONN2,related,NODE1,NODE2,
```

## License

This project is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License (CC-BY-NC-SA 4.0). This means you are free to:

- Share — copy and redistribute the material in any medium or format
- Adapt — remix, transform, and build upon the material

Under the following terms:
- Attribution — You must give appropriate credit, provide a link to the license, and indicate if changes were made
- NonCommercial — You may not use the material for commercial purposes
- ShareAlike — If you remix, transform, or build upon the material, you must distribute your contributions under the same license as the original

See the [LICENSE](LICENSE) file for details. 