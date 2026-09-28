"""
config.py — Central configuration for the agentic celiac diagnosis system.

All paths, model names, and tuneable parameters live here so that every
other module can ``from pheno_agent.config import cfg``.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Path constants (relative to project root)
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "stuttering"
RESULTS_DIR = Path("results")

# Phenotype
PHENOTYPE = "stuttering"
USE_LABS = False  # Lab values are not needed for stuttering

# Input data
EHR_MARKDOWN_DIR = DATA_DIR / "ehr_markdown_dataset"
LAB_CSV_PATH = None
KEYWORDS_PATH = DATA_DIR / "stuttering_keywords.yaml"
DIAGNOSIS_LOGIC_PATH = DATA_DIR / "stuttering_rules.md"
GROUND_TRUTH_PATH = None

# ChromaDB
CHROMA_DB_PATH = DATA_DIR / "chroma_db"
NOTES_COLLECTION_NAME = "stuttering_notes"
LABS_COLLECTION_NAME = ""

# BioClinicalBERT (used by ChromaDB retriever)
EMBED_MODEL_LOCAL = Path("/home/biand/Projects/Celiac_BioVU/models/Bio_ClinicalBERT")
EMBED_MODEL_HF = "emilyalsentzer/Bio_ClinicalBERT"
EMBED_MODEL = str(EMBED_MODEL_LOCAL) if EMBED_MODEL_LOCAL.exists() else EMBED_MODEL_HF

# Output
AGENT_RESULTS_DIR = RESULTS_DIR / "stuttering"
AGENT_RESULTS_CSV = RESULTS_DIR / "stuttering_results.csv"


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------
@dataclass
class ModelConfig:
    """Ollama model assignments for each agent role."""

    # Strong reasoning — used by Critic and Adjudicator
    reasoning_model: str = "qwen3.8:27b"

    # Structured extraction — used by Signal Extractor
    extraction_model: str = "qwen3.6:35b-a3b"

    # Fast / lightweight — used by Data Gatherer summarisation
    fast_model: str = "qwen3.6:35b-a3b"


# ---------------------------------------------------------------------------
# Agent parameters
# ---------------------------------------------------------------------------
@dataclass
class AgentConfig:
    """Tuneable agent parameters."""

    # Maximum reflection loops (Extractor ↔ Critic)
    max_reflection_loops: int = 2

    # LLM generation settings
    temperature: float = 0.0
    seed: int = 42

    # Retrieval settings
    top_k_chunks: int = 20

    # Notes batching for Signal Extractor (notes per LLM call)
    extraction_batch_size: int = 5
    extraction_max_chars_per_batch: int = 15000  # Dynamic batching character budget
    extraction_concurrency: int = 3  # Parallel batch calls via ThreadPoolExecutor

    # Ollama connection
    use_remote_ollama: bool = True  # Set to True to use the remote GPU via SSH tunnel
    ollama_host_local: str = "http://localhost:11434"
    ollama_host_remote: str = "http://localhost:11435"
    
    @property 
    def ollama_host(self) -> str:
        return self.ollama_host_remote if self.use_remote_ollama else self.ollama_host_local

    ollama_timeout: int = 300  # seconds — reasoning / general timeout
    extraction_timeout: int = 120  # seconds — per-batch extraction timeout


# ---------------------------------------------------------------------------
# Assembled config singleton
# ---------------------------------------------------------------------------
@dataclass
class Config:
    """Top-level configuration container."""

    models: ModelConfig = field(default_factory=ModelConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    phenotype: str = PHENOTYPE
    use_labs: bool = USE_LABS
    project_root: Path = PROJECT_ROOT
    data_dir: Path = DATA_DIR
    results_dir: Path = RESULTS_DIR
    ehr_markdown_dir: Path = EHR_MARKDOWN_DIR
    lab_csv_path: Optional[Path] = LAB_CSV_PATH
    keywords_path: Path = KEYWORDS_PATH
    diagnosis_logic_path: Path = DIAGNOSIS_LOGIC_PATH
    ground_truth_path: Optional[Path] = GROUND_TRUTH_PATH
    chroma_db_path: Path = CHROMA_DB_PATH
    notes_collection_name: str = NOTES_COLLECTION_NAME
    labs_collection_name: str = LABS_COLLECTION_NAME
    embed_model: str = EMBED_MODEL
    agent_results_dir: Path = AGENT_RESULTS_DIR
    agent_results_csv: Path = AGENT_RESULTS_CSV


# Module-level singleton — import this everywhere
cfg = Config()
