# OpenWarrant

[![CI](https://github.com/tan2line/openwarrant/actions/workflows/ci.yml/badge.svg)](https://github.com/tan2line/openwarrant/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18666989.svg)](https://doi.org/10.5281/zenodo.18666989)

**Machine-readable authority for AI agents and autonomous systems.**

OpenWarrant implements the **warrants-as-skills** paradigm: governance checks are native upstream dependencies in the execution graph that are externally authored, cryptographically signed, and institutionally issued. Agents and autonomous systems may execute under warrants but never author their own authority.

Zero framework dependencies. The core works from the CLI, as a Python/TypeScript import, or inside agent frameworks through optional thin adapters.

## Autonomy Profile — OWAP v0.1

The experimental **OpenWarrant Autonomy Profile (OWAP) v0.1** extends the warrant primitive to physical and cyber-physical autonomous systems. It binds authority to a specific system identity and configuration and makes permitted actions, prohibited actions, operating-envelope limits, human-control requirements, evidence obligations, validity, and revocation machine-readable.

**Evidence supports authority. Authority bounds autonomy. Operation generates evidence.**

See [`profiles/autonomy/README.md`](profiles/autonomy/README.md) for the profile specification, [`profiles/autonomy/owap-v0.1.schema.json`](profiles/autonomy/owap-v0.1.schema.json) for the JSON Schema, and [`profiles/autonomy/reference/owap_runtime.py`](profiles/autonomy/reference/owap_runtime.py) for the reference evaluator. The included example is deliberately non-kinetic: a synthetic critical-infrastructure inspection system.

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

See [docs/architecture.md](docs/architecture.md) for the core specification.

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

```text
openwarrant/
├── docs/                    # Core architecture spec and warrant schema
├── examples/                # Agent-governance simulation and warrants
├── profiles/
│   └── autonomy/            # OWAP v0.1 schema, examples, test vectors, reference runtime
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
- **Autonomous systems** — machine-readable operating authority through OWAP v0.1

## Contributing

See [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

## Citation

```bibtex
@software{plummer2026openwarrant,
  author = {Plummer, Andrew D.},
  title = {OpenWarrant: Machine-Readable Authority for AI Agents and Autonomous Systems},
  year = {2026},
  version = {0.1.0},
  license = {Apache-2.0}
}
```

## License

Apache 2.0 — see [LICENSE](LICENSE).
