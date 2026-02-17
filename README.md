# OpenWarrant

[![CI](https://github.com/tan2line/openwarrant/actions/workflows/ci.yml/badge.svg)](https://github.com/tan2line/openwarrant/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18666989.svg)](https://doi.org/10.5281/zenodo.18666989)

**A runtime-agnostic governance library for AI agents.**

OpenWarrant implements the **warrants-as-skills** paradigm: governance checks are native agent skills — upstream dependencies in the execution graph that are externally authored, cryptographically signed, and institutionally issued. Agents execute warrants but never author them.

Zero framework dependencies. Works from the CLI, as a Python/TypeScript import, or inside any agent framework through optional thin adapters.

## Quick Start

### Python

```bash
pip install -e packages/core-python
```

```python
from openwarrant import WarrantEngine, WarrantRequest

engine = WarrantEngine(warrant_store="./examples/warrants/")

response = engine.check(WarrantRequest(
    agent_id="agent-001",
    action="read-patient-record",
    role="attending_physician",
    data_type="PHI",
    context={"patient_consent": True, "recipient_verified": True},
))

print(response.decision)  # Decision.AUTHORIZED
```

### CLI

```bash
openwarrant check \
  --action read-patient-record \
  --role attending_physician \
  --data-type PHI \
  --warrant-dir examples/warrants/ \
  --context '{"patient_consent": true, "recipient_verified": true}'
```

### TypeScript

```bash
cd packages/core-typescript && npm install
```

```typescript
import { WarrantEngine, Decision } from '@openwarrant/core';

const engine = new WarrantEngine({ warrantStore: './examples/warrants/' });

const response = engine.check({
  agentId: 'agent-001',
  action: 'read-patient-record',
  role: 'attending_physician',
  dataType: 'PHI',
  context: { patient_consent: true, recipient_verified: true },
});

console.log(response.decision); // "AUTHORIZED"
```

## Decision Types

| Decision | Meaning |
|----------|---------|
| `AUTHORIZED` | Valid warrant, all conditions met — proceed |
| `DENIED` | Warrant exists but conditions not met — blocked |
| `ESCALATE` | Within scope but requires human review |
| `NO_WARRANT` | No applicable warrant found — cannot act |
| `EXPIRED` | Matching warrant found but expired |

## Architecture

OpenWarrant has five core components:

1. **Warrant Engine** — Pattern-matching engine that checks requests against loaded warrants
2. **Warrant Store** — YAML files with Ed25519 signatures, human-readable and cryptographically verifiable
3. **Skill Dependency Graph** — DAG resolver ensuring governance skills execute before action skills
4. **Audit Chain** — SHA-256 hash-linked tamper-evident records
5. **Trust Escalation** — Agents earn trust through governed execution (Level 0-4)

See [docs/architecture.md](docs/architecture.md) for the full specification.

## Running Tests

```bash
# Python
cd packages/core-python
pip install -e ".[dev]"
pytest

# TypeScript
cd packages/core-typescript
npm install
npx vitest run
```

## Project Structure

```
openwarrant/
├── docs/                    # Architecture spec and warrant schema
├── examples/
│   ├── simulation.html      # Interactive governance simulation
│   └── warrants/            # Example warrants (healthcare, finance, insurance)
├── packages/
│   ├── core-python/         # Python core library (zero deps)
│   └── core-typescript/     # TypeScript core library
├── CITATION.cff
├── LICENSE
└── README.md
```

## Domains

- **Healthcare** — HIPAA-compliant PHI disclosure warrants
- **Finance** — Fiduciary trade execution warrants
- **Insurance** — Claims processing warrants

## Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

## Citation

```bibtex
@software{plummer2026openwarrant,
  author = {Plummer, Andrew D.},
  title = {OpenWarrant: A Runtime-Agnostic Governance Library for AI Agents},
  year = {2026},
  version = {0.1.0},
  license = {Apache-2.0}
}
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
