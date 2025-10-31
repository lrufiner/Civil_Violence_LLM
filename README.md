# Civil Violence LLM

Epstein's civil violence model enhanced with Large Language Models (LLM) for agent decision-making.

## Description

This project implements Model 1 from the article "Modeling civil violence: An agent-based computational approach" by Joshua Epstein ([PNAS, 2002](https://www.pnas.org/content/99/suppl_3/7243.full)), with the innovation of using language models (LLM) to simulate citizen decision-making processes.

### Key Features

- **Agent-based simulation** using [Mesa](https://mesa.readthedocs.io/)
- **LLM-powered decisions**: Citizens use Ollama (phi3 model) to decide whether to rebel
- **Interactive visualization** with [Solara](https://solara.dev/)
- **Dynamic parameters**: Adjust legitimacy, vision, and jail terms in real-time without restarting
- **Hybrid approach**: P % of agents use LLM, 100-P % use mathematical rules for performance
- **Console logging**: Monitor LLM responses with agent IDs and decision factors
- **Agents**:
  - **Citizens**: Make rebellion decisions based on grievance and risk aversion
  - **Cops**: Arrest active citizens within their vision range

## Requirements

- Python 3.11+
- [Ollama](https://ollama.ai/) installed with the `phi3` model o similar

## Installation

1. Clone the repository:

```bash
git clone https://github.com/lrufiner/Civil_Violence_LLM.git
cd Civil_Violence_LLM
```

2. Create and activate a virtual environment:

```bash
python3.11 -m venv .venv
source .venv/bin/activate  # On Linux/Mac
# .venv\Scripts\activate  # On Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Install and configure Ollama:

```bash
# Install Ollama from https://ollama.ai/
# Download the phi3 model
ollama pull phi3
```

## Usage

### Run the simulation with visualization

```bash
source .venv/bin/activate
solara run app.py
```

Then open your browser at: `http://localhost:8765`

### Run in background

```bash
nohup solara run app.py > solara.log 2>&1 &
```

## Project Structure

```text
Civil_Violence_LLM/
├── agents.py                    # Agent definitions (Citizens and Cops)
├── model.py                     # Main simulation model
├── app.py                       # Solara visualization interface
├── config.py                    # Centralized configuration file
├── requirements.txt             # Python dependencies
├── README.md                    # This file
└── CONFIG_GUIDE.md              # Configuration guide
```

## Model Parameters

### Initial Parameters (require restart)

- **`citizen_density`**: Initial citizen density (0-1)
- **`cop_density`**: Initial cop density (0-1)
- **`height/width`**: Grid dimensions

### Dynamic Parameters (update in real-time)

- **`legitimacy`**: Government legitimacy perception (0-1)
  - Low values = high grievance = more rebellion
  - High values = low grievance = less rebellion
- **`citizen_vision`**: Citizen vision radius (cells)
- **`cop_vision`**: Cop vision radius (cells)
- **`max_jail_term`**: Maximum jail sentence

### LLM Configuration (in config.py)

- **`llm_usage_rate`**: Percentage of agents using LLM (default: 1%)
- **`model`**: Ollama model to use (default: "phi3")
- **`max_response_tokens`**: Max words in LLM response (default: 10)
- **`prompt_template`**: Prompt used for LLM queries

## Citizen States

- 🟠 **ACTIVE**: In rebellion against the regime
- 🔵 **QUIET**: Not in rebellion
- ⚫ **ARRESTED**: In jail

## Interface Controls

### Initial Model Parameters Panel (Left)

Adjusting these parameters **restarts the simulation**:

- Initial Agent Density
- Initial Cop Density
- Citizen Vision
- Cop Vision
- Government Legitimacy
- Max Jail Term
- Random Seed

### Live Settings Panel (Right)

Adjusting these parameters **updates in real-time without restart**:

- 🏛️ **Legitimacy**: Changes grievance calculation immediately
- 👁️ **Citizen Vision**: Updates citizen perception range
- 🚔 **Cop Vision**: Updates cop arrest range
- ⚖️ **Jail Term**: Affects new arrests only

### Console Output

Monitor LLM decisions in the terminal:

```text
🤖 Agent 123 | G:75% R:20% | LLM responded: 'yes, rebel'
```

- **G**: Grievance percentage
- **R**: Risk aversion percentage

## Technologies Used

- [Mesa](https://mesa.readthedocs.io/) - Agent-based modeling framework
- [Solara](https://solara.dev/) - Reactive web visualization framework
- [Ollama](https://ollama.ai/) - Local LLM engine
- [Matplotlib](https://matplotlib.org/) - Data visualization
- [NetworkX](https://networkx.org/) - Network analysis

## Performance Optimization

The simulation uses a **hybrid approach** for performance:

- **1% of agents** use LLM for decisions (~11 agents per step)
- **99% of agents** use mathematical rules (instant)
- This balance provides LLM examples while maintaining speed

To adjust LLM usage, edit `config.py`:

```python
LLM_CONFIG = {
    "llm_usage_rate": 0.05,  # 5% instead of 1%
}
```

## Credits

Based on the original work by:

- Epstein, J. M. (2002). "Modeling civil violence: An agent-based computational approach". *Proceedings of the National Academy of Sciences*, 99(suppl 3), 7243-7250.

## License

This project is under the MIT license. See the `LICENSE` file for details.

## Contributing

Contributions are welcome. Please:

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Author

Juan Aued (modified by Leonardo Rufiner)
